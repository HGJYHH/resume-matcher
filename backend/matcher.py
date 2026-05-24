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
    # 从新的结构化字段中提取文本
    text_parts = []

    # 求职意向
    if resume_info.get("job_intention"):
        text_parts.append(resume_info["job_intention"])

    # 教育经历
    for edu in resume_info.get("educations", []):
        edu_text = " ".join(filter(None, [
            edu.get("school", ""),
            edu.get("major", ""),
            edu.get("degree", "")
        ]))
        if edu_text.strip():
            text_parts.append(edu_text)

    # 项目经历
    for proj in resume_info.get("projects", []):
        proj_text = " ".join(filter(None, [
            proj.get("name", ""),
            proj.get("description", ""),
            " ".join(proj.get("technologies", []))
        ]))
        if proj_text.strip():
            text_parts.append(proj_text)

    resume_skills_text = " ".join(text_parts)

    # 提取关键词
    resume_keywords = set(extract_keywords(resume_skills_text))
    job_keywords = set(extract_keywords(job_desc))

    # 技能匹配率
    if job_keywords:
        skill_match_rate = len(resume_keywords & job_keywords) / len(job_keywords)
    else:
        skill_match_rate = 0.0

    # 工作经验得分（基于工作年限与岗位要求中出现的年份数字的简单比较）
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
        experience_score = 1.0  # 无要求则满分

    # 综合评分（简单加权）
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