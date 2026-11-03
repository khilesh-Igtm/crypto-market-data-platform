from datetime import datetime, timezone
from decimal import Decimal
from app.exchanges.binance.schemas import BinanceTickerPriceResponse
from app.exchanges.binance.normalizer import normalize_ticker_price

def test_normalize_ticker_price():
    response = BinanceTickerPriceResponse(
        symbol="BTCUSDT",
        price=Decimal("77236.01000000")
    )
    result = normalize_ticker_price(response)
    
    assert result.exchange == "binance"
    assert result.symbol == "BTCUSDT"
    assert result.price == Decimal("77236.01000000")
    assert result.fetched_at.tzinfo == timezone.utc
    assert isinstance(result.fetched_at, datetime)