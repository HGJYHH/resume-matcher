# 项目代码上下文

> 扫描范围：.

## 项目目录结构 (目标范围: .\.)
```text
./
    .env
    backend/
        ai_extract.py
        app.py
        cache.py
        config.py
        matcher.py
        pdf_parser.py
        requirements.txt
    front/
        index.html
```

## 每一个文件的代码内容

### 文件路径: `.env`
```text
AI_API_KEY=sk-1bb975e4f74545bb9a2d5b971c6b56b9
AI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_MODEL=qwen-plus
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
CACHE_TTL=3600
```

### 文件路径: `backend\ai_extract.py`
```python
# backend/ai_extract.py
import json
import re
from openai import OpenAI
from config import AI_API_KEY, AI_API_BASE, AI_MODEL

client = OpenAI(api_key=AI_API_KEY, base_url=AI_API_BASE)


def extract_resume_info(resume_text: str) -> dict:
    """
    使用 AI 模型从简历文本中提取结构化信息。
    返回包含基本信息、求职信息、背景信息的字典。
    """
    prompt = f"""你是一个专业的简历解析助手。请从以下简历文本中提取关键信息，并以严格的 JSON 格式返回。
如果没有找到某个字段，请用 null 表示。

需要提取的字段：
- name: 姓名
- phone: 电话号码
- email: 邮箱
- address: 地址
- job_intention: 求职意向（可能没有，则为 null）
- expected_salary: 期望薪资（可能没有，则为 null）
- work_years: 工作年限（可能没有，则为 null）
- education: 学历背景（可能没有，则为 null）
- project_experience: 项目经历（可能没有，则为 null，如果有，简要总结为一段文本）

简历文本：
{resume_text}

只返回一个 JSON 对象，不要包含任何其他文字。"""

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        # 尝试直接解析 JSON
        try:
            info = json.loads(content)
        except json.JSONDecodeError:
            # 容错：用正则提取第一个 JSON 对象
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                info = json.loads(match.group())
            else:
                raise ValueError("无法从回复中提取 JSON")

        # 确保字段都存在
        fields = ["name", "phone", "email", "address", "job_intention",
                  "expected_salary", "work_years", "education", "project_experience"]
        for f in fields:
            info.setdefault(f, None)
        return info

    except Exception as e:
        # 失败时返回空结构
        print(f"AI extract error: {e}")
        return {
            "name": None, "phone": None, "email": None, "address": None,
            "job_intention": None, "expected_salary": None,
            "work_years": None, "education": None, "project_experience": None
        }
```

### 文件路径: `backend\app.py`
```python
import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from flask_cors import CORS

from pdf_parser import extract_text_from_pdf
from ai_extract import extract_resume_info
from matcher import rule_based_match, ai_match
from cache import get_cached_result, set_cached_result
from config import MAX_CONTENT_LENGTH, AI_API_KEY

app = Flask(__name__)      # 先创建 app 实例
CORS(app)                  # 再配置跨域

# 下面继续写你的路由...
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/parse', methods=['POST'])
def parse_resume():
    """
    接口：上传简历 PDF，返回解析结果、关键信息、匹配度评分（需同时传 job_desc）。
    """
    # 检查文件
    if 'file' not in request.files:
        return jsonify({"code": 400, "message": "未找到文件"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"code": 400, "message": "文件名为空"}), 400
    if not allowed_file(file.filename):
        return jsonify({"code": 400, "message": "只允许上传 PDF 文件"}), 400

    # 读取文件内容
    file_bytes = file.read()
    try:
        resume_text = extract_text_from_pdf(file_bytes)
    except Exception as e:
        return jsonify({"code": 500, "message": f"PDF 解析失败: {str(e)}"}), 500

    if not resume_text.strip():
        return jsonify({"code": 400, "message": "未能从 PDF 中提取到有效文本"}), 400

    # 岗位描述（用于匹配评分）
    job_desc = request.form.get('job_desc', '').strip()
    use_ai_match = request.form.get('use_ai_match', 'false').lower() == 'true'

    # 尝试从缓存获取
    cached = get_cached_result(resume_text + job_desc) if job_desc else get_cached_result(resume_text)
    if cached:
        return jsonify({"code": 200, "data": cached, "message": "来自缓存"})

    # 1. AI 提取关键信息
    ai_info = extract_resume_info(resume_text)

    # 2. 匹配度评分
    match_result = None
    if job_desc:
        if use_ai_match and AI_API_KEY != "your-api-key":
            # 尝试 AI 匹配
            match_result = ai_match(resume_text, job_desc)
        if not match_result:
            # 回退到规则匹配
            match_result = rule_based_match(ai_info, job_desc)
    else:
        match_result = None

    # 构建返回结果
    result = {
        "resume_text": resume_text[:500] + "..." if len(resume_text) > 500 else resume_text,  # 截断预览
        "info": ai_info,
        "match": match_result
    }

    # 写入缓存
    if job_desc:
        set_cached_result(resume_text + job_desc, result)
    else:
        set_cached_result(resume_text, result)

    return jsonify({"code": 200, "data": result, "message": "解析成功"})


@app.errorhandler(413)
def too_large(e):
    return jsonify({"code": 413, "message": "文件大小超过限制"}), 413


# 本地运行入口
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### 文件路径: `backend\cache.py`
```python
import json
import hashlib
from config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB, CACHE_TTL

# 尝试导入 redis，若失败则使用内存模拟（本地开发可接受）
try:
    import redis
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        db=REDIS_DB,
        decode_responses=True
    )
    # 测试连接
    redis_client.ping()
    USE_REDIS = True
except Exception:
    print("Redis 不可用，使用内存缓存（仅用于开发环境）")
    USE_REDIS = False
    _memory_cache = {}


def _hash_content(content: str) -> str:
    return hashlib.md5(content.encode()).hexdigest()


def get_cached_result(resume_text: str) -> dict | None:
    """根据简历文本获取缓存的解析+评分结果"""
    key = _hash_content(resume_text)
    if USE_REDIS:
        data = redis_client.get(key)
        if data:
            return json.loads(data)
    else:
        return _memory_cache.get(key)
    return None


def set_cached_result(resume_text: str, result: dict, ttl: int = CACHE_TTL):
    """缓存结果"""
    key = _hash_content(resume_text)
    value = json.dumps(result, ensure_ascii=False)
    if USE_REDIS:
        redis_client.setex(key, ttl, value)
    else:
        _memory_cache[key] = result
```

### 文件路径: `backend\config.py`
```python
# backend/config.py
from dotenv import load_dotenv
load_dotenv()

import os

AI_API_KEY = os.getenv("AI_API_KEY")                # 必须设置，不能留空
AI_API_BASE = os.getenv("AI_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
AI_MODEL = os.getenv("AI_MODEL", "qwen-plus")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_DB = int(os.getenv("REDIS_DB", 0))
CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
```

### 文件路径: `backend\matcher.py`
```python
# backend/matcher.py
import json
import re
from collections import Counter
from openai import OpenAI
from config import AI_API_KEY, AI_API_BASE, AI_MODEL

client = OpenAI(api_key=AI_API_KEY, base_url=AI_API_BASE)


def extract_keywords(text: str) -> list:
    """
    简单的中英文关键词提取（基于正则分词 + 词频），用于技能匹配。
    """
    words = re.findall(r'[a-zA-Z]+|[\u4e00-\u9fff]+', text.lower())
    words = [w for w in words if len(w) > 1]
    word_counts = Counter(words)
    keywords = [word for word, _ in word_counts.most_common(20)]
    return keywords


def rule_based_match(resume_info: dict, job_desc: str) -> dict:
    """
    基于规则的匹配度评分（基础版），返回匹配分数字典。
    """
    resume_skills_text = " ".join([
        resume_info.get("job_intention") or "",
        resume_info.get("education") or "",
        resume_info.get("project_experience") or ""
    ])

    resume_keywords = set(extract_keywords(resume_skills_text))
    job_keywords = set(extract_keywords(job_desc))

    if job_keywords:
        skill_match_rate = len(resume_keywords & job_keywords) / len(job_keywords)
    else:
        skill_match_rate = 0.0

    year_pattern = r'(\d+)\s*年'
    job_years = re.findall(year_pattern, job_desc)
    required_years = max([int(y) for y in job_years]) if job_years else None
    work_years_str = resume_info.get("work_years")
    try:
        actual_years = float(work_years_str) if work_years_str else 0
    except:
        actual_years = 0

    if required_years and required_years > 0:
        experience_score = min(actual_years / required_years, 1.0)
    else:
        experience_score = 1.0

    overall_score = round((0.6 * skill_match_rate + 0.4 * experience_score) * 100, 2)

    return {
        "overall_score": overall_score,
        "skill_match_rate": round(skill_match_rate * 100, 2),
        "experience_score": round(experience_score * 100, 2),
        "details": {
            "resume_keywords": list(resume_keywords),
            "job_keywords": list(job_keywords),
            "matched_keywords": list(resume_keywords & job_keywords),
            "required_years": required_years,
            "actual_years": actual_years
        }
    }


def ai_match(resume_text: str, job_desc: str) -> dict:
    """
    使用 AI 模型进行更精准的匹配度评分（加分项）。
    返回包含评分和理由的字典，失败则返回 None。
    """
    prompt = f"""你是一个专业的招聘匹配度评估专家。请根据以下简历内容和岗位描述，评估候选人与岗位的匹配度。
给出 0-100 的综合评分，并简要说明理由（包括技能匹配程度、工作经验相关性、学历适配度等）。

简历内容：
{resume_text}

岗位描述：
{job_desc}

请以严格的 JSON 格式返回评估结果，格式如下：
{{
  "overall_score": 85,
  "skill_match_rate": 90,
  "experience_score": 80,
  "reason": "技能高度匹配，但工作年限略低于要求..."
}}
只返回 JSON，不要包含其他文字。"""

    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        # 尝试直接解析 JSON，失败则用正则提取
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                result = json.loads(match.group())
            else:
                raise ValueError("无法从回复中提取 JSON")
        return result
    except Exception as e:
        print(f"AI match error: {e}")
        return None
```

### 文件路径: `backend\pdf_parser.py`
```python
import io
import re
import pdfplumber


def extract_text_from_pdf(file_stream: bytes) -> str:
    """
    从 PDF 文件二进制流中提取所有页面的文本，并进行基础清洗。
    """
    full_text = []
    with pdfplumber.open(io.BytesIO(file_stream)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)

    raw_text = "\n".join(full_text)
    cleaned = clean_text(raw_text)
    return cleaned


def clean_text(text: str) -> str:
    """
    清洗文本：去除多余空白、特殊字符，保留可读格式。
    """
    # 将多个空白字符（含换行、制表）压缩为单个空格
    text = re.sub(r"\s+", " ", text)
    # 移除控制字符（保留常用标点）
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # 合并多个空格
    text = re.sub(r" +", " ", text)
    return text.strip()
```

### 文件路径: `backend\requirements.txt`
```text
Flask==3.0.3
pdfplumber==0.10.3
openai==1.30.1
redis==5.0.4
python-dotenv==1.0.1
gunicorn==22.0.0
```

### 文件路径: `front\index.html`
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>简历智能匹配系统</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; color: #333; }
    .container { max-width: 800px; margin: 40px auto; background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); padding: 30px; }
    h1 { text-align: center; margin-bottom: 30px; color: #2c3e50; }
    .section { margin-bottom: 25px; }
    label { display: block; margin-bottom: 8px; font-weight: 600; color: #4a5568; }
    input[type="file"] { width: 100%; padding: 12px; border: 2px dashed #cbd5e0; border-radius: 8px; font-size: 16px; }
    textarea { width: 100%; padding: 12px; border: 2px solid #cbd5e0; border-radius: 8px; font-size: 16px; height: 120px; resize: vertical; }
    input[type="file"]:hover, textarea:hover { border-color: #4299e1; }
    button { background: #4299e1; color: white; border: none; padding: 12px 30px; border-radius: 8px; font-size: 16px; cursor: pointer; transition: background 0.3s; }
    button:hover { background: #3182ce; }
    button:disabled { background: #a0aec0; cursor: not-allowed; }
    .result-box { margin-top: 30px; background: #f7fafc; border-radius: 8px; padding: 20px; border: 1px solid #e2e8f0; }
    .result-box h3 { margin-bottom: 15px; color: #2d3748; }
    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .info-item { background: white; padding: 8px 12px; border-radius: 6px; }
    .info-item strong { color: #4a5568; }
    .match-score { font-size: 2em; font-weight: bold; color: #2b6cb0; text-align: center; margin: 15px 0; }
    .details { margin-top: 15px; }
    .error { color: #e53e3e; font-weight: bold; }
    .loading { text-align: center; padding: 20px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>📄 简历智能解析与岗位匹配</h1>

    <div class="section">
      <label for="resumeFile">上传简历（PDF）</label>
      <input type="file" id="resumeFile" accept=".pdf">
    </div>

    <div class="section">
      <label for="jobDesc">岗位需求描述（选填，用于匹配评分）</label>
      <textarea id="jobDesc" placeholder="请输入招聘岗位的要求和描述..."></textarea>
    </div>

    <button id="submitBtn" onclick="submitForm()">开始解析与匹配</button>

    <div id="result" class="result-box" style="display: none;"></div>
  </div>

  <script>
    // 修改为你的后端 API 地址（本地测试保持 localhost:5000）
    const API_BASE = 'http://localhost:5000';

    async function submitForm() {
      const fileInput = document.getElementById('resumeFile');
      const jobDesc = document.getElementById('jobDesc').value.trim();
      const resultDiv = document.getElementById('result');
      const btn = document.getElementById('submitBtn');

      if (!fileInput.files[0]) {
        alert('请先选择简历文件');
        return;
      }

      const formData = new FormData();
      formData.append('file', fileInput.files[0]);
      if (jobDesc) {
        formData.append('job_desc', jobDesc);
        // 可选：是否使用 AI 精确匹配，默认 false，可改为 true 尝试 AI 评分
        formData.append('use_ai_match', 'false');
      }

      resultDiv.style.display = 'block';
      resultDiv.innerHTML = '<div class="loading">⏳ 正在解析中，请稍候...</div>';
      btn.disabled = true;

      try {
        const response = await fetch(`${API_BASE}/parse`, {
          method: 'POST',
          body: formData
        });
        const res = await response.json();

        if (res.code === 200) {
          renderResult(res.data, res.message);
        } else {
          resultDiv.innerHTML = `<div class="error">错误: ${res.message}</div>`;
        }
      } catch (err) {
        resultDiv.innerHTML = `<div class="error">请求失败: ${err.message}</div>`;
      } finally {
        btn.disabled = false;
      }
    }

    function renderResult(data, message) {
      const info = data.info || {};
      const match = data.match;
      let html = `<h3>✅ ${message}</h3>`;

      // 基本信息
      html += `<div class="info-grid">
        <div class="info-item"><strong>姓名:</strong> ${info.name || '未识别'}</div>
        <div class="info-item"><strong>电话:</strong> ${info.phone || '未识别'}</div>
        <div class="info-item"><strong>邮箱:</strong> ${info.email || '未识别'}</div>
        <div class="info-item"><strong>地址:</strong> ${info.address || '未识别'}</div>
        <div class="info-item"><strong>求职意向:</strong> ${info.job_intention || '无'}</div>
        <div class="info-item"><strong>期望薪资:</strong> ${info.expected_salary || '无'}</div>
        <div class="info-item"><strong>工作年限:</strong> ${info.work_years || '无'}</div>
        <div class="info-item"><strong>学历:</strong> ${info.education || '无'}</div>
      </div>`;

      if (info.project_experience) {
        html += `<div style="margin-top:10px"><strong>项目经历:</strong><br>${info.project_experience}</div>`;
      }

      if (match) {
        html += `<div class="match-score">综合匹配度: ${match.overall_score}%</div>`;
        html += `<div class="details">
          <p>技能匹配率: ${match.skill_match_rate}%</p>
          <p>经验匹配度: ${match.experience_score}%</p>
          ${match.reason ? `<p><strong>AI 分析:</strong> ${match.reason}</p>` : ''}
        </div>`;
      }

      document.getElementById('result').innerHTML = html;
    }
  </script>
</body>
</html>
```

