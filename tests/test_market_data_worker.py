import asyncio
from datetime import timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

import app.workers.market_data_worker as worker_module
from app.exchanges.binance.schemas import BinanceTickerPriceResponse
from app.workers.market_data_worker import (
    MarketDataIngestionWorker,
    parse_symbols,
)


class FakeClient:
    async def get_ticker_price(self, symbol: str):
        return BinanceTickerPriceResponse(
            symbol=symbol,
            price=Decimal("65000.50"),
        )


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None


def test_parse_symbols():
    result = parse_symbols(
        "BTCUSDT, ETHUSDT, btcusdt, BNBUSDT"
    )

    assert result == [
        "BTCUSDT",
        "ETHUSDT",
        "BNBUSDT",
    ]


@pytest.mark.asyncio
async def test_ingest_symbol_persists_market_price(monkeypatch):
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

    persisted = []

    async def fake_persist_market_price(
        session,
        market_price,
        cache=None,
    ):
        persisted.append(market_price)

    monkeypatch.setattr(
        worker_module,
        "persist_market_price",
        fake_persist_market_price,
    )

    worker = MarketDataIngestionWorker(
        client=FakeClient(),
        session_factory=FakeSession,
        symbols=["BTCUSDT"],
    )

    result = await worker.ingest_symbol("BTCUSDT")

    assert result is True
    assert len(persisted) == 1

    saved_price = persisted[0]

    assert saved_price.exchange == "binance"
    assert saved_price.symbol == "BTCUSDT"
    assert saved_price.price == Decimal("65000.50")
    assert saved_price.fetched_at.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_ingest_symbol_handles_exchange_failure(monkeypatch):
    monkeypatch.setattr(
        worker_module,
        "get_settings",
        lambda: SimpleNamespace(
            ingestion_symbols="BTCUSDT",
            ingestion_poll_interval_seconds=5.0,
            database_max_retries=2,
            database_retry_base_seconds=0.5,
        ),
    )

    class FailingClient:
        async def get_ticker_price(self, symbol: str):
            raise RuntimeError("Exchange unavailable")

    worker = MarketDataIngestionWorker(
        client=FailingClient(),
        session_factory=FakeSession,
        symbols=["BTCUSDT"],
    )

    result = await worker.ingest_symbol("BTCUSDT")

    assert result is False


@pytest.mark.asyncio
async def test_worker_does_not_start_when_shutdown_requested(
    monkeypatch,
):
    monkeypatch.setattr(
        worker_module,
        "get_settings",
        lambda: SimpleNamespace(
            ingestion_symbols="BTCUSDT",
            ingestion_poll_interval_seconds=5.0,
            database_max_retries=2,
            database_retry_base_seconds=0.5,
        ),
    )

    stop_event = asyncio.Event()
    stop_event.set()

    worker = MarketDataIngestionWorker(
        client=FakeClient(),
        session_factory=FakeSession,
        symbols=["BTCUSDT"],
        stop_event=stop_event,
    )

    await worker.run()