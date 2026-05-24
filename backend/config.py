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