from decimal import Decimal
from pydantic import BaseModel, Field


class BinanceTickerPriceResponse(BaseModel):
    symbol: str = Field(min_length=1)
    price: Decimal = Field(gt=0)