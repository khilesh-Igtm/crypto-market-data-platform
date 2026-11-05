import pytest
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.db.base import Base
from app.db.models import Exchange, MarketPriceRecord  # noqa: F401


@pytest.fixture(scope="session")
def test_database_url():
    settings = get_settings()

    database_name = "crypto_market_data_test"

    if database_name == settings.database_name:
        raise RuntimeError(
            "Tests must never run against the development database."
        )

    return URL.create(
        drivername="postgresql+asyncpg",
        username=settings.database_user,
        password=settings.database_password.get_secret_value(),
        host=settings.database_host,
        port=settings.database_port,
        database=database_name,
    )


@pytest.fixture
async def db_session(test_database_url):
    test_engine = create_async_engine(
        test_database_url,
        pool_pre_ping=True,
    )

    try:
        async with test_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with test_engine.connect() as connection:
            transaction = await connection.begin()

            session_factory = async_sessionmaker(
                bind=connection,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                join_transaction_mode="create_savepoint",
            )

            try:
                async with session_factory() as session:
                    yield session
            finally:
                if transaction.is_active:
                    await transaction.rollback()

        async with test_engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)

    finally:
        await test_engine.dispose()