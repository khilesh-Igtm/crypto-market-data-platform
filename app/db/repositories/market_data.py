from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Exchange, MarketPriceRecord
from app.market_data.schemas import MarketPrice


class MarketDataRepository:
    """
    Handles database operations related to exchanges
    and market price records.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_exchange(self, name: str) -> Exchange | None:
        statement = select(Exchange).where(
            Exchange.name == name
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def create_exchange(self, name: str) -> Exchange:
        exchange = Exchange(name=name)

        self.session.add(exchange)

        await self.session.flush()

        return exchange

    async def add_market_price(
        self,
        exchange_id: int,
        market_price: MarketPrice,
    ) -> MarketPriceRecord:

        record = MarketPriceRecord(
            exchange_id=exchange_id,
            symbol=market_price.symbol,
            price=market_price.price,
            fetched_at=market_price.fetched_at,
        )

        self.session.add(record)

        await self.session.flush()

        return record

    async def get_latest_price(
        self,
        exchange_name: str,
        symbol: str,
    ) -> MarketPriceRecord | None:

        statement = (
            select(MarketPriceRecord)
            .join(Exchange)
            .where(
                Exchange.name == exchange_name,
                MarketPriceRecord.symbol == symbol,
            )
            .order_by(
                MarketPriceRecord.fetched_at.desc(),
                MarketPriceRecord.id.desc(),
            )
            .limit(1)
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def get_price_history(
        self,
        exchange_name: str,
        symbol: str,
        limit: int = 100,
    ) -> list[MarketPriceRecord]:

        if limit <= 0:
            raise ValueError("Limit must be greater than zero")

        statement = (
            select(MarketPriceRecord)
            .join(Exchange)
            .where(
                Exchange.name == exchange_name,
                MarketPriceRecord.symbol == symbol,
            )
            .order_by(
                MarketPriceRecord.fetched_at.desc(),
                MarketPriceRecord.id.desc(),
            )
            .limit(limit)
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())