from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.exchanges.binance.schemas import BinanceTickerPriceResponse
from app.market_data.schemas import (
    MarketPrice,
    MarketPriceHistoryResponse,
    MarketPriceResponse,
)


def test_market_price_accepts_valid_data():
    price = MarketPrice(
        exchange="binance",
        symbol="BTCUSDT",
        price=Decimal("70000.123456789123456789"),
        fetched_at=datetime.now(timezone.utc),
    )

    assert price.price == Decimal("70000.123456789123456789")


@pytest.mark.parametrize(
    "invalid_price",
    [
        Decimal("0"),
        Decimal("-1"),
    ],
)
def test_market_price_rejects_non_positive_price(invalid_price):
    with pytest.raises(ValidationError):
        MarketPrice(
            exchange="binance",
            symbol="BTCUSDT",
            price=invalid_price,
            fetched_at=datetime.now(timezone.utc),
        )


def test_market_price_is_immutable():
    price = MarketPrice(
        exchange="binance",
        symbol="BTCUSDT",
        price=Decimal("70000"),
        fetched_at=datetime.now(timezone.utc),
    )

    with pytest.raises(ValidationError):
        price.symbol = "ETHUSDT"


def test_binance_schema_rejects_invalid_price():
    with pytest.raises(ValidationError):
        BinanceTickerPriceResponse(
            symbol="BTCUSDT",
            price="-100",
        )


def test_binance_schema_rejects_empty_symbol():
    with pytest.raises(ValidationError):
        BinanceTickerPriceResponse(
            symbol="",
            price="70000",
        )


def test_market_price_response_accepts_exchange_string():
    response = MarketPriceResponse(
        id=1,
        exchange="binance",
        symbol="BTCUSDT",
        price=Decimal("70000"),
        fetched_at=datetime.now(timezone.utc),
    )

    assert response.exchange == "binance"


def test_history_response_structure():
    response = MarketPriceHistoryResponse(
        exchange="binance",
        symbol="BTCUSDT",
        limit=100,
        offset=0,
        has_more=False,
        prices=[],
    )

    assert response.prices == []
    assert response.has_more is False