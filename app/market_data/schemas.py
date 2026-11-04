from datetime import datetime
from decimal import Decimal

from pydantic import (
    AliasChoices,
    AliasPath,
    BaseModel,
    ConfigDict,
    Field,
)


class MarketPrice(BaseModel):
    """
    Normalized market data received from an exchange.
    """

    model_config = ConfigDict(frozen=True)

    exchange: str
    symbol: str
    price: Decimal = Field(gt=0)
    fetched_at: datetime


class MarketPriceResponse(BaseModel):
    """
    API response representing a single market price record.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    exchange: str = Field(
        validation_alias=AliasChoices(
            AliasPath("exchange", "name"),
            "exchange",
        )
    )
    symbol: str
    price: Decimal
    fetched_at: datetime


class MarketPriceHistoryResponse(BaseModel):
    """
    API response containing paginated historical market prices.
    """

    exchange: str
    symbol: str

    limit: int
    offset: int
    has_more: bool

    prices: list[MarketPriceResponse]