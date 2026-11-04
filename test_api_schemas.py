from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.market_data.schemas import (
    MarketPrice,
    MarketPriceHistoryResponse,
    MarketPriceResponse,
)


def test_market_price_response():

    exchange = SimpleNamespace(name="binance")

    record = SimpleNamespace(
        id=101,
        exchange=exchange,
        symbol="BTCUSDT",
        price=Decimal("77684.71"),
        fetched_at=datetime.now(UTC),
    )

    response = MarketPriceResponse.model_validate(record)

    assert response.id == 101
    assert response.exchange == "binance"
    assert response.symbol == "BTCUSDT"

    print(response.model_dump())


def test_market_price_history_response():

    price = MarketPriceResponse(
        id=101,
        exchange="binance",
        symbol="BTCUSDT",
        price=Decimal("77684.71"),
        fetched_at=datetime.now(UTC),
    )

    history = MarketPriceHistoryResponse(
        exchange="binance",
        symbol="BTCUSDT",
        prices=[price],
    )

    assert len(history.prices) == 1

    print(history.model_dump())


def test_normalized_market_price():

    price = MarketPrice(
        exchange="binance",
        symbol="BTCUSDT",
        price=Decimal("77684.71"),
        fetched_at=datetime.now(UTC),
    )

    assert price.price > 0

    print(price)