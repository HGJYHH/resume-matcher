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