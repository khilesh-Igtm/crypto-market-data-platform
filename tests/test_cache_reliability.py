import pytest
from redis.exceptions import RedisError

from app.cache.redis import RedisCache


@pytest.mark.asyncio
async def test_invalid_json_returns_none():
    class InvalidJSONRedis:
        async def get(self, key):
            return "{invalid-json"

    cache = RedisCache(InvalidJSONRedis())

    assert await cache.get_json("test:key") is None


@pytest.mark.asyncio
async def test_cache_serialization_failure():
    class FakeRedis:
        async def set(self, *args, **kwargs):
            raise AssertionError("Redis should not be called")

    cache = RedisCache(FakeRedis())

    result = await cache.set_json(
        "test:key",
        {"invalid": object()},
        ttl=30,
    )

    assert result is False


@pytest.mark.asyncio
async def test_delete_failure_returns_false():
    class BrokenRedis:
        async def delete(self, *args):
            raise RedisError("Redis unavailable")

    cache = RedisCache(BrokenRedis())

    assert await cache.delete("test:key") is False


@pytest.mark.asyncio
async def test_invalidation_deletes_multiple_history_keys():
    class FakeRedis:
        def __init__(self):
            self.deleted = []

        async def delete(self, *keys):
            self.deleted.extend(keys)

        async def scan_iter(self, match, count):
            for key in [
                "market:v1:history:binance:BTCUSDT:100:0",
                "market:v1:history:binance:BTCUSDT:50:0",
            ]:
                yield key

    client = FakeRedis()
    cache = RedisCache(client)

    await cache.invalidate_market_data(
        "BINANCE",
        "btcusdt",
    )

    assert "market:v1:latest:binance:BTCUSDT" in client.deleted

    assert (
        "market:v1:history:binance:BTCUSDT:100:0"
        in client.deleted
    )

    assert (
        "market:v1:history:binance:BTCUSDT:50:0"
        in client.deleted
    )


@pytest.mark.asyncio
async def test_invalidation_handles_scan_failure():
    class BrokenRedis:
        def __init__(self):
            self.deleted = []

        async def delete(self, *keys):
            self.deleted.extend(keys)

        async def scan_iter(self, **kwargs):
            raise RedisError("Redis unavailable")
            yield

    client = BrokenRedis()
    cache = RedisCache(client)

    await cache.invalidate_market_data(
        "binance",
        "BTCUSDT",
    )

    assert "market:v1:latest:binance:BTCUSDT" in client.deleted