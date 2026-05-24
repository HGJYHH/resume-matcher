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