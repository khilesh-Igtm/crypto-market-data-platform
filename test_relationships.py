from datetime import datetime, timezone
from decimal import Decimal

from app.db.models import Exchange, MarketPriceRecord

exchange = Exchange(name="binance")

price = MarketPriceRecord(
    symbol="BTCUSDT",
    price=Decimal("77415.47000000"),
    fetched_at=datetime.now(timezone.utc),
)

price.exchange = exchange

assert price.exchange.name == "binance"
assert len(exchange.market_prices) == 1
assert exchange.market_prices[0].symbol == "BTCUSDT"

print("All ORM relationship tests passed!")