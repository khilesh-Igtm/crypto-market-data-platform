from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.db.repositories.market_data import MarketDataRepository
from app.market_data.schemas import MarketPrice
from app.market_data.service import persist_market_price


@pytest.mark.asyncio
async def test_create_exchange(db_session):
    repository = MarketDataRepository(db_session)

    exchange = await repository.create_exchange("binance")

    assert exchange.id is not None
    assert exchange.name == "binance"


@pytest.mark.asyncio
async def test_persist_market_price(db_session):
    market_price = MarketPrice(
        exchange="binance",
        symbol="BTCUSDT",
        price=Decimal("77684.71"),
        fetched_at=datetime.now(timezone.utc),
    )

    record = await persist_market_price(db_session, market_price)

    assert record.id is not None
    assert record.exchange_id is not None
    assert record.symbol == "BTCUSDT"
    assert record.price == Decimal("77684.71")


@pytest.mark.asyncio
async def test_reuse_existing_exchange(db_session):
    first_price = MarketPrice(
        exchange="binance",
        symbol="BTCUSDT",
        price=Decimal("77000"),
        fetched_at=datetime.now(timezone.utc),
    )

    second_price = MarketPrice(
        exchange="binance",
        symbol="ETHUSDT",
        price=Decimal("3000"),
        fetched_at=datetime.now(timezone.utc),
    )

    first_record = await persist_market_price(db_session, first_price)
    second_record = await persist_market_price(db_session, second_price)

    assert first_record.exchange_id == second_record.exchange_id


@pytest.mark.asyncio
async def test_get_latest_price(db_session):
    now = datetime.now(timezone.utc)

    older_price = MarketPrice(
        exchange="binance",
        symbol="BTCUSDT",
        price=Decimal("75000"),
        fetched_at=now - timedelta(minutes=5),
    )

    newer_price = MarketPrice(
        exchange="binance",
        symbol="BTCUSDT",
        price=Decimal("78000"),
        fetched_at=now,
    )

    await persist_market_price(db_session, older_price)
    await persist_market_price(db_session, newer_price)

    repository = MarketDataRepository(db_session)

    latest = await repository.get_latest_price("binance", "BTCUSDT")

    assert latest is not None
    assert latest.price == Decimal("78000")


@pytest.mark.asyncio
async def test_get_price_history(db_session):
    now = datetime.now(timezone.utc)

    for index in range(3):
        market_price = MarketPrice(
            exchange="binance",
            symbol="BTCUSDT",
            price=Decimal("75000") + index,
            fetched_at=now + timedelta(minutes=index),
        )

        await persist_market_price(db_session, market_price)

    repository = MarketDataRepository(db_session)

    history = await repository.get_price_history(
        exchange_name="binance",
        symbol="BTCUSDT",
        limit=2,
    )

    assert len(history) == 2
    assert history[0].price == Decimal("75002")
    assert history[1].price == Decimal("75001")


@pytest.mark.asyncio
async def test_invalid_history_limit(db_session):
    repository = MarketDataRepository(db_session)

    with pytest.raises(ValueError, match="Limit must be greater than zero"):
        await repository.get_price_history(
            exchange_name="binance",
            symbol="BTCUSDT",
            limit=0,
        )