import logging

from sqlalchemy import text

from app.db.session import engine

logger = logging.getLogger(__name__)


async def check_database() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True

    except Exception:
        logger.exception("Database health check failed")
        return False