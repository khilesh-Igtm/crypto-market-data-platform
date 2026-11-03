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