from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.dependencies import get_redis_cache
from app.cache.redis import RedisCache
from app.db.session import get_db_session

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/health/database")
async def database_health_check(
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> dict[str, str]:

    try:
        result = await session.execute(text("SELECT 1"))

        if result.scalar_one() != 1:
            raise HTTPException(
                status_code=503,
                detail="Database health check failed",
            )

        return {"status": "database_connected"}

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable",
        ) from exc


@router.get("/health/redis")
async def redis_health_check(
    cache: Annotated[
        RedisCache,
        Depends(get_redis_cache),
    ],
) -> dict[str, str]:

    if not await cache.ping():
        raise HTTPException(
            status_code=503,
            detail="Redis is unavailable",
        )

    return {"status": "redis_connected"}