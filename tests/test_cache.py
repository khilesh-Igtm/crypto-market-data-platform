from datetime import datetime, timezone
from decimal import Decimal

import fakeredis.aioredis
import pytest
from redis.exceptions import RedisError

from app.cache.redis import RedisCache
from app.market_data.schemas import MarketPrice
from app.market_data.service import (
    get_latest_market_price,
    persist_market_price,
)


@pytest.fixture
async def redis_cache():
    client = fakeredis.aioredis.FakeRedis(
        decode_responses=True,
    )

    yield RedisCache(client)

    await client.aclose()


@pytest.mark.asyncio
async def test_cache_set_and_get(redis_cache):
    data = {
        "symbol": "BTCUSDT",
        "price": "77684.71000000",
    }

    success = await redis_cache.set_json(
        "test:btc",
        data,
        ttl=30,
    )

    assert success is True
    assert await redis_cache.get_json("test:btc") == data


@pytest.mark.asyncio
async def test_cache_ttl(redis_cache):
    await redis_cache.set_json(
        "test:ttl",
        {"value": 1},
        ttl=30,
    )

    ttl = await redis_cache.client.ttl("test:ttl")

    assert 0 < ttl <= 30


@pytest.mark.asyncio
async def test_cache_invalidation(redis_cache):
    await redis_cache.set_json(
        "market:v1:latest:binance:BTCUSDT",
        {"price": "70000"},
        ttl=30,
    )

    await redis_cache.set_json(
        "market:v1:history:binance:BTCUSDT:100:0:none:none",
        [],
        ttl=30,
    )

    await redis_cache.invalidate_market_data(
        "binance",
        "BTCUSDT",
    )

    assert await redis_cache.get_json(
        "market:v1:latest:binance:BTCUSDT"
    ) is None

    assert await redis_cache.get_json(
        "market:v1:history:binance:BTCUSDT:100:0:none:none"
    ) is None


@pytest.mark.asyncio
async def test_redis_failure_does_not_crash():
    class BrokenRedis:
        async def get(self, key):
            raise RedisError("Redis unavailable")

        async def set(self, *args, **kwargs):
            raise RedisError("Redis unavailable")

        async def delete(self, *args):
            raise RedisError("Redis unavailable")

        async def ping(self):
            raise RedisError("Redis unavailable")

    cache = RedisCache(BrokenRedis())

    assert await cache.get_json("test:key") is None

    assert await cache.set_json(
        "test:key",
        {"value": 1},
        ttl=30,
    ) is False

    assert await cache.ping() is False


@pytest.mark.asyncio
async def test_database_fallback_when_redis_fails(db_session):
    class BrokenRedis:
        async def get(self, key):
            raise RedisError("Redis unavailable")

        async def set(self, *args, **kwargs):
            raise RedisError("Redis unavailable")

        async def delete(self, *args):
            raise RedisError("Redis unavailable")

    cache = RedisCache(BrokenRedis())

    market_price = MarketPrice(
        exchange="binance",
        symbol="BTCUSDT",
        price=Decimal("77684.71000000"),
        fetched_at=datetime.now(timezone.utc),
    )

    await persist_market_price(
        db_session,
        market_price,
    )

    result = await get_latest_market_price(
        session=db_session,
        exchange_name="binance",
        symbol="BTCUSDT",
        cache=cache,
    )

    assert result is not None
    assert result.symbol == "BTCUSDT"
    assert result.price == Decimal("77684.71000000")