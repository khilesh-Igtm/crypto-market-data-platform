from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from app.api.v1.router import api_router
from app.cache.redis import RedisCache
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.db.session import engine


@asynccontextmanager
async def lifespan(application: FastAPI):
    settings = get_settings()

    redis_client = Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )

    application.state.redis_client = redis_client
    application.state.redis_cache = RedisCache(redis_client)

    try:
        yield

    finally:
        try:
            await redis_client.aclose()
        finally:
            await engine.dispose()

def create_app() -> FastAPI:
    settings = get_settings()

    setup_logging()

    application = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    application.add_middleware(RequestContextMiddleware)
    register_exception_handlers(application)

    application.include_router(
        api_router,
        prefix=settings.api_v1_prefix,
    )

    return application


app = create_app()