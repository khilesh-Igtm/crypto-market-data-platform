from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.market_data.schemas import (
    MarketPriceHistoryResponse,
    MarketPriceResponse,
)
from app.market_data.service import (
    get_latest_market_price,
    get_market_price_history,
)

router = APIRouter(
    prefix="/market-data",
    tags=["Market Data"],
)


@router.get(
    "/latest/{symbol}",
    response_model=MarketPriceResponse,
)
async def latest_market_price(
    symbol: Annotated[str, Path(min_length=1, max_length=30)],
    exchange: Annotated[str, Query(min_length=1, max_length=50)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MarketPriceResponse:
    """
    Retrieve the latest market price for an exchange and symbol.
    """

    record = await get_latest_market_price(
        session=session,
        exchange_name=exchange,
        symbol=symbol,
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Market price not found",
        )

    return MarketPriceResponse.model_validate(record)


@router.get(
    "/history/{symbol}",
    response_model=MarketPriceHistoryResponse,
)
async def market_price_history(
    symbol: Annotated[str, Path(min_length=1, max_length=30)],
    exchange: Annotated[str, Query(min_length=1, max_length=50)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> MarketPriceHistoryResponse:

    if (
        start_time is not None
        and end_time is not None
        and start_time > end_time
    ):
        raise HTTPException(
            status_code=422,
            detail="start_time must be earlier than or equal to end_time",
        )

    records = await get_market_price_history(
        session=session,
        exchange_name=exchange,
        symbol=symbol,
        limit=limit + 1,
        offset=offset,
        start_time=start_time,
        end_time=end_time,
    )

    has_more = len(records) > limit
    records = records[:limit]

    return MarketPriceHistoryResponse(
        exchange=exchange,
        symbol=symbol,
        limit=limit,
        offset=offset,
        has_more=has_more,
        prices=[
            MarketPriceResponse.model_validate(record)
            for record in records
        ],
    )