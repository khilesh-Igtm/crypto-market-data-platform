from datetime import datetime, timezone

from app.exchanges.binance.schemas import (
    BinanceTickerPriceResponse
)

from app.market_data.schemas import MarketPrice


def normalize_ticker_price(
    response: BinanceTickerPriceResponse
) -> MarketPrice:

    return MarketPrice(
        exchange="binance",
        symbol=response.symbol,
        price=response.price,
        fetched_at=datetime.now(timezone.utc)
    )