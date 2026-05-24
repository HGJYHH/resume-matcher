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