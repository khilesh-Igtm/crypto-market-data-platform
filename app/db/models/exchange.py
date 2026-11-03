from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models.market_price import MarketPriceRecord
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Exchange(Base):
    __tablename__ = "exchanges"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    market_prices: Mapped[list["MarketPriceRecord"]] = relationship(
        back_populates="exchange",
        cascade="all, delete-orphan",
    )