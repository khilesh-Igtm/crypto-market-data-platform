from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session

router = APIRouter(
    tags=["Health"],
)


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Check whether the application is running.
    """

    return {
        "status": "healthy"
    }


@router.get("/health/database")
async def database_health_check(
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> dict[str, str]:
    """
    Check whether the database is accessible.
    """

    try:
        result = await session.execute(text("SELECT 1"))

        if result.scalar_one() != 1:
            raise HTTPException(
                status_code=503,
                detail="Database health check failed",
            )

        return {
            "status": "database_connected"
        }

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable",
        ) from exc