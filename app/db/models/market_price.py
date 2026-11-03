from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models.exchange import Exchange
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MarketPriceRecord(Base):
    __tablename__ = "market_prices"

    __table_args__ = (
        CheckConstraint(
            "price > 0",
            name="ck_market_prices_price_positive",
        ),
        Index(
            "ix_market_prices_exchange_symbol_fetched",
            "exchange_id",
            "symbol",
            "fetched_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )

    exchange_id: Mapped[int] = mapped_column(
        ForeignKey("exchanges.id", ondelete="RESTRICT"),
        nullable=False,
    )

    symbol: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(38, 18),
        nullable=False,
    )

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    exchange: Mapped["Exchange"] = relationship(
        back_populates="market_prices",
    )