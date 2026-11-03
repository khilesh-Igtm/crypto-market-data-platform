from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MarketPrice(BaseModel):

    model_config = ConfigDict(frozen=True)

    exchange: str
    symbol: str
    price: Decimal = Field(gt=0)
    fetched_at: datetime