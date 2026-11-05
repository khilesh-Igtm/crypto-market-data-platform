import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import OperationalError

import app.workers.market_data_worker as worker_module
from app.market_data.schemas import MarketPrice
from app.workers.market_data_worker import MarketDataIngestionWorker


@pytest.fixture
def worker_settings(monkeypatch):
    monkeypatch.setattr(
        worker_module,
        "get_settings",
        lambda: SimpleNamespace(
            ingestion_symbols="BTCUSDT,ETHUSDT",
            ingestion_poll_interval_seconds=5.0,
            database_max_retries=2,
            database_retry_base_seconds=0.5,
        ),
    )


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None


def test_worker_rejects_empty_symbols(worker_settings):
    with pytest.raises(ValueError, match="At least one"):
        MarketDataIngestionWorker(
            symbols=[],
        )


def test_worker_rejects_invalid_poll_interval(worker_settings):
    with pytest.raises(ValueError, match="Poll interval"):
        MarketDataIngestionWorker(
            symbols=["BTCUSDT"],
            poll_interval=0,
        )


@pytest.mark.asyncio
async def test_database_retry_succeeds(worker_settings, monkeypatch):
    attempts = []
    delays = []
    sessions_created = []

    class Session(FakeSession):
        pass

    def session_factory():
        session = Session()
        sessions_created.append(session)
        return session

    async def fake_persist(session, market_price, cache=None):
        attempts.append(session)

        if len(attempts) < 3:
            raise OperationalError(
                "INSERT",
                {},
                Exception("Database unavailable"),
            )

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(
        worker_module,
        "persist_market_price",
        fake_persist,
    )
    monkeypatch.setattr(
        worker_module.asyncio,
        "sleep",
        fake_sleep,
    )

    worker = MarketDataIngestionWorker(
        client=object(),
        session_factory=session_factory,
        symbols=["BTCUSDT"],
    )

    market_price = MarketPrice(
        exchange="binance",
        symbol="BTCUSDT",
        price=Decimal("70000"),
        fetched_at=datetime.now(timezone.utc)
    )

    await worker._persist_with_retry(market_price)

    assert len(attempts) == 3
    assert len(sessions_created) == 3
    assert len(set(map(id, attempts))) == 3
    assert delays == [0.5, 1.0]


@pytest.mark.asyncio
async def test_database_retry_exhaustion(worker_settings, monkeypatch):
    attempts = 0
    delays = []

    async def fake_persist(session, market_price, cache=None):
        nonlocal attempts
        attempts += 1

        raise OperationalError(
            "INSERT",
            {},
            Exception("Database unavailable"),
        )

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(
        worker_module,
        "persist_market_price",
        fake_persist,
    )
    monkeypatch.setattr(
        worker_module.asyncio,
        "sleep",
        fake_sleep,
    )

    worker = MarketDataIngestionWorker(
        client=object(),
        session_factory=FakeSession,
        symbols=["BTCUSDT"],
    )

    market_price = MarketPrice(
        exchange="binance",
        symbol="BTCUSDT",
        price=Decimal("70000"),
        fetched_at=datetime.now(timezone.utc)
    )

    with pytest.raises(OperationalError):
        await worker._persist_with_retry(market_price)

    assert attempts == 3
    assert delays == [0.5, 1.0]


@pytest.mark.asyncio
async def test_ingest_once_counts_successful_symbols(worker_settings, monkeypatch):
    class MixedClient:
        async def get_ticker_price(self, symbol):
            if symbol == "ETHUSDT":
                raise RuntimeError("Exchange unavailable")

            from app.exchanges.binance.schemas import (
                BinanceTickerPriceResponse,
            )

            return BinanceTickerPriceResponse(
                symbol=symbol,
                price=Decimal("70000"),
            )

    persisted = []

    async def fake_persist(session, market_price, cache=None):
        persisted.append(market_price.symbol)

    worker = MarketDataIngestionWorker(
        client=MixedClient(),
        session_factory=FakeSession,
        symbols=["BTCUSDT", "ETHUSDT"],
    )

    # try block hata diya aur uske andar ke code ka indentation theek kar diya
    monkeypatch.setattr(
        worker_module,
        "persist_market_price",
        fake_persist,
    )

    result = await worker.ingest_once()

    assert result == 1
    assert persisted == ["BTCUSDT"]

@pytest.mark.asyncio
async def test_worker_propagates_cancellation(worker_settings):
    class CancelledClient:
        async def get_ticker_price(self, symbol):
            raise asyncio.CancelledError()

    worker = MarketDataIngestionWorker(
        client=CancelledClient(),
        session_factory=FakeSession,
        symbols=["BTCUSDT"],
    )

    with pytest.raises(asyncio.CancelledError):
        await worker.ingest_symbol("BTCUSDT")