from fastapi import Request

from app.cache.redis import RedisCache


def get_redis_cache(request: Request) -> RedisCache:
    return request.app.state.redis_cache