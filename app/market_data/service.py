from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MarketPriceRecord
from app.db.repositories.market_data import MarketDataRepository
from app.market_data.schemas import MarketPrice


async def persist_market_price(
    session: AsyncSession,
    market_price: MarketPrice,
) -> MarketPriceRecord:
    """
    Persist a normalized market price in the database.
    """

    repository = MarketDataRepository(session)

    async with session.begin():
        exchange = await repository.get_exchange(
            market_price.exchange
        )

        if exchange is None:
            exchange = await repository.create_exchange(
                market_price.exchange
            )

        record = await repository.add_market_price(
            exchange_id=exchange.id,
            market_price=market_price,
        )

    return record

async def get_latest_market_price(
    session: AsyncSession,
    exchange_name: str,
    symbol: str,
) -> MarketPriceRecord | None:
    """
    Retrieve the latest market price for an exchange and symbol.
    """

    repository = MarketDataRepository(session)

    return await repository.get_latest_price(
        exchange_name=exchange_name,
        symbol=symbol,
    )


async def get_market_price_history(
    session: AsyncSession,
    exchange_name: str,
    symbol: str,
    limit: int = 100,
    offset: int = 0,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[MarketPriceRecord]:

    repository = MarketDataRepository(session)

    return await repository.get_price_history(
        exchange_name=exchange_name,
        symbol=symbol,
        limit=limit,
        offset=offset,
        start_time=start_time,
        end_time=end_time,
    )