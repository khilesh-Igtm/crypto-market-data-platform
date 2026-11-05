from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

import app.market_data.service as service


class FakeCache:
    def __init__(self, initial=None):
        self.data = initial or {}
        self.deleted = []
        self.written = []

    async def get_json(self, key):
        return self.data.get(key)

    async def set_json(self, key, value, ttl):
        self.data[key] = value
        self.written.append((key, value, ttl))
        return True

    async def delete(self, key):
        self.deleted.append(key)
        self.data.pop(key, None)
        return True


class FakeRepository:
    def __init__(self, session):
        self.latest_calls = 0
        self.history_calls = 0
        self.latest_record = None
        self.history_records = []

    async def get_latest_price(self, **kwargs):
        self.latest_calls += 1
        return self.latest_record

    async def get_price_history(self, **kwargs):
        self.history_calls += 1
        return self.history_records


@pytest.fixture
def fake_settings(monkeypatch):
    monkeypatch.setattr(
        service,
        "get_settings",
        lambda: SimpleNamespace(
            latest_price_cache_ttl=5,
            history_cache_ttl=60,
        ),
    )


def make_record(price="70000.50"):
    return SimpleNamespace(
        id=1,
        exchange=SimpleNamespace(name="binance"),
        symbol="BTCUSDT",
        price=Decimal(price),
        fetched_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_latest_cache_hit_skips_database(
    monkeypatch,
    fake_settings,
):
    cached_data = {
        "id": 1,
        "exchange": "binance",
        "symbol": "BTCUSDT",
        "price": "70000.50",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    cache = FakeCache(
        {
            service.latest_cache_key("BINANCE", "btcusdt"): cached_data
        }
    )

    repository = FakeRepository(None)

    monkeypatch.setattr(
        service,
        "MarketDataRepository",
        lambda session: repository,
    )

    result = await service.get_latest_market_price(
        session=object(),
        exchange_name="BINANCE",
        symbol="btcusdt",
        cache=cache,
    )

    assert result is not None
    assert result.symbol == "BTCUSDT"
    assert result.price == Decimal("70000.50")
    assert repository.latest_calls == 0


@pytest.mark.asyncio
async def test_latest_cache_miss_reads_database(
    monkeypatch,
    fake_settings,
):
    repository = FakeRepository(None)
    repository.latest_record = make_record()

    monkeypatch.setattr(
        service,
        "MarketDataRepository",
        lambda session: repository,
    )

    cache = FakeCache()

    result = await service.get_latest_market_price(
        session=object(),
        exchange_name="binance",
        symbol="BTCUSDT",
        cache=cache,
    )

    assert result is not None
    assert result.price == Decimal("70000.50")
    assert repository.latest_calls == 1
    assert len(cache.written) == 1
    assert cache.written[0][2] == 5


@pytest.mark.asyncio
async def test_latest_price_not_found(
    monkeypatch,
    fake_settings,
):
    repository = FakeRepository(None)

    monkeypatch.setattr(
        service,
        "MarketDataRepository",
        lambda session: repository,
    )

    result = await service.get_latest_market_price(
        session=object(),
        exchange_name="binance",
        symbol="UNKNOWN",
    )

    assert result is None
    assert repository.latest_calls == 1


@pytest.mark.asyncio
async def test_invalid_latest_cache_is_deleted(
    monkeypatch,
    fake_settings,
):
    key = service.latest_cache_key("binance", "BTCUSDT")

    cache = FakeCache({key: {"invalid": "payload"}})

    repository = FakeRepository(None)
    repository.latest_record = make_record()

    monkeypatch.setattr(
        service,
        "MarketDataRepository",
        lambda session: repository,
    )

    result = await service.get_latest_market_price(
        session=object(),
        exchange_name="binance",
        symbol="BTCUSDT",
        cache=cache,
    )

    assert result is not None
    assert key in cache.deleted
    assert repository.latest_calls == 1


@pytest.mark.asyncio
async def test_history_cache_hit(
    monkeypatch,
    fake_settings,
):
    cached_record = {
        "id": 1,
        "exchange": "binance",
        "symbol": "BTCUSDT",
        "price": "70000",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    key = service.history_cache_key(
        "binance",
        "BTCUSDT",
        100,
        0,
        None,
        None,
    )

    cache = FakeCache({key: [cached_record]})
    repository = FakeRepository(None)

    monkeypatch.setattr(
        service,
        "MarketDataRepository",
        lambda session: repository,
    )

    result = await service.get_market_price_history(
        session=object(),
        exchange_name="binance",
        symbol="BTCUSDT",
        cache=cache,
    )

    assert len(result) == 1
    assert result[0].price == Decimal("70000")
    assert repository.history_calls == 0


@pytest.mark.asyncio
async def test_history_cache_miss_reads_database(
    monkeypatch,
    fake_settings,
):
    repository = FakeRepository(None)
    repository.history_records = [
        make_record("70000"),
        make_record("71000"),
    ]

    monkeypatch.setattr(
        service,
        "MarketDataRepository",
        lambda session: repository,
    )

    cache = FakeCache()

    result = await service.get_market_price_history(
        session=object(),
        exchange_name="binance",
        symbol="BTCUSDT",
        limit=10,
        cache=cache,
    )

    assert len(result) == 2
    assert repository.history_calls == 1
    assert len(cache.written) == 1
    assert cache.written[0][2] == 60


def test_latest_cache_key_normalization():
    first = service.latest_cache_key(
        "BINANCE",
        "btcusdt",
    )

    second = service.latest_cache_key(
        "binance",
        "BTCUSDT",
    )

    assert first == second


def test_history_cache_key_includes_pagination():
    first = service.history_cache_key(
        "binance",
        "BTCUSDT",
        100,
        0,
        None,
        None,
    )

    second = service.history_cache_key(
        "binance",
        "BTCUSDT",
        100,
        10,
        None,
        None,
    )

    assert first != second