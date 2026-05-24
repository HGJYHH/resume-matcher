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
    教育经历和项目经历为列表格式。
    """
    prompt = f"""你是一个专业的简历解析助手。请从以下简历文本中提取关键信息，并以严格的 JSON 格式返回。
如果没有找到某个字段，请用 null 表示（列表类型用空数组 [] 表示）。

需要提取的字段：
- name: 姓名 (字符串)
- phone: 电话号码 (字符串)
- email: 邮箱 (字符串)
- address: 地址 (字符串)
- job_intention: 求职意向 (字符串，可能没有，则为 null)
- expected_salary: 期望薪资 (字符串，可能没有，则为 null)
- work_years: 工作年限 (字符串，可能没有，则为 null)
- educations: 教育经历列表 (数组)，每个元素是一个对象，包含：
   - school: 学校名称 (字符串)
   - major: 专业 (字符串)
   - degree: 学历层次，如本科、硕士、大专等 (字符串)
   - start_date: 开始时间，只保留年份，如 "2024" (字符串)
   - end_date: 结束时间，只保留年份，如 "2026" (字符串)
   如果未提取到教育经历，则返回空数组 []。
- projects: 项目经历列表 (数组)，每个元素是一个对象，包含：
   - name: 项目名称 (字符串)
   - duration: 项目时间，如 "2026.02-2026.05" (字符串)
   - description: 项目描述，简要总结项目背景、职责和成果 (字符串)
   - technologies: 使用到的技术栈列表，如 ["Spring Boot", "Redis", "WebSocket"] (字符串数组)
   如果未提取到项目经历，则返回空数组 []。

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

        # 规范化字段：确保新字段（educations、projects）存在且格式正确
        info = _normalize_fields(info)

        return info

    except Exception as e:
        # 失败时返回空结构
        print(f"AI extract error: {e}")
        return {
            "name": None, "phone": None, "email": None, "address": None,
            "job_intention": None, "expected_salary": None,
            "work_years": None,
            "educations": [],
            "projects": []
        }


def _normalize_fields(info: dict) -> dict:
    """确保所有字段都存在，并将旧版字段转换为新结构"""
    # 基本字段默认值
    info.setdefault("name", None)
    info.setdefault("phone", None)
    info.setdefault("email", None)
    info.setdefault("address", None)
    info.setdefault("job_intention", None)
    info.setdefault("expected_salary", None)
    info.setdefault("work_years", None)

    # 处理教育经历：兼容旧字段 education 和新的 educations
    if "educations" not in info and "education" in info:
        # 如果 AI 返回了旧版 education 字符串，转换为列表
        edu_str = info.pop("education")
        if isinstance(edu_str, str) and edu_str.strip():
            info["educations"] = [{"school": "", "major": "", "degree": "", "start_date": "", "end_date": "", "raw": edu_str}]
        else:
            info["educations"] = []
    else:
        info.setdefault("educations", [])

    # 确保 educations 是列表
    if not isinstance(info["educations"], list):
        info["educations"] = []

    # 处理项目经历：兼容旧字段 project_experience 和新的 projects
    if "projects" not in info and "project_experience" in info:
        proj_str = info.pop("project_experience")
        if isinstance(proj_str, str) and proj_str.strip():
            info["projects"] = [{"name": "", "duration": "", "description": proj_str, "technologies": []}]
        else:
            info["projects"] = []
    else:
        info.setdefault("projects", [])

    if not isinstance(info["projects"], list):
        info["projects"] = []

    return info