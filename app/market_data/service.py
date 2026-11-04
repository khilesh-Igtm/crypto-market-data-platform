from datetime import datetime

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis import RedisCache
from app.core.config import get_settings
from app.db.models import MarketPriceRecord
from app.db.repositories.market_data import MarketDataRepository
from app.market_data.schemas import MarketPrice, MarketPriceResponse


def latest_cache_key(exchange: str, symbol: str) -> str:
    return (
        f"market:v1:latest:"
        f"{exchange.lower()}:{symbol.upper()}"
    )


def history_cache_key(
    exchange: str,
    symbol: str,
    limit: int,
    offset: int,
    start_time: datetime | None,
    end_time: datetime | None,
) -> str:
    return (
        f"market:v1:history:"
        f"{exchange.lower()}:{symbol.upper()}:"
        f"{limit}:{offset}:"
        f"{start_time.isoformat() if start_time else 'none'}:"
        f"{end_time.isoformat() if end_time else 'none'}"
    )


async def persist_market_price(
    session: AsyncSession,
    market_price: MarketPrice,
    cache: RedisCache | None = None,
) -> MarketPriceRecord:
    """Persist normalized market data and invalidate related cache."""

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

    if cache is not None:
        await cache.invalidate_market_data(
            market_price.exchange,
            market_price.symbol,
        )

    return record


async def get_latest_market_price(
    session: AsyncSession,
    exchange_name: str,
    symbol: str,
    cache: RedisCache | None = None,
) -> MarketPriceResponse | None:
    """Retrieve latest price using cache-aside strategy."""

    settings = get_settings()

    key = latest_cache_key(exchange_name, symbol)

    if cache is not None:
        cached = await cache.get_json(key)

        if cached is not None:
            try:
                return MarketPriceResponse.model_validate(cached)

            except ValidationError:
                await cache.delete(key)

    repository = MarketDataRepository(session)

    record = await repository.get_latest_price(
        exchange_name=exchange_name,
        symbol=symbol,
    )

    if record is None:
        return None

    response = MarketPriceResponse.model_validate(record)

    if cache is not None:
        await cache.set_json(
            key,
            response.model_dump(mode="json"),
            settings.latest_price_cache_ttl,
        )

    return response


async def get_market_price_history(
    session: AsyncSession,
    exchange_name: str,
    symbol: str,
    limit: int = 100,
    offset: int = 0,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    cache: RedisCache | None = None,
) -> list[MarketPriceResponse]:
    """Retrieve historical prices using cache-aside strategy."""

    settings = get_settings()

    key = history_cache_key(
        exchange_name,
        symbol,
        limit,
        offset,
        start_time,
        end_time,
    )

    if cache is not None:
        cached = await cache.get_json(key)

        if cached is not None:
            try:
                return [
                    MarketPriceResponse.model_validate(item)
                    for item in cached
                ]

            except (ValidationError, TypeError):
                await cache.delete(key)

    repository = MarketDataRepository(session)

    records = await repository.get_price_history(
        exchange_name=exchange_name,
        symbol=symbol,
        limit=limit,
        offset=offset,
        start_time=start_time,
        end_time=end_time,
    )

    responses = [
        MarketPriceResponse.model_validate(record)
        for record in records
    ]

    if cache is not None:
        await cache.set_json(
            key,
            [
                response.model_dump(mode="json")
                for response in responses
            ],
            settings.history_cache_ttl,
        )

    return responses