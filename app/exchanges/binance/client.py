import asyncio
import logging
from collections.abc import Awaitable, Callable

import httpx
from pydantic import ValidationError

from app.core.config import get_settings
from app.exchanges.binance.schemas import BinanceTickerPriceResponse
from app.exchanges.exceptions import (
    ExchangeAPIError,
    ExchangeConnectionError,
    ExchangeError,
    ExchangeRateLimitError,
    ExchangeResponseError,
    ExchangeTimeoutError,
    ExchangeUnavailableError,
)

logger = logging.getLogger(__name__)


class BinanceClient:
    BASE_URL = "https://api.binance.com"

    def __init__(
        self,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        settings = get_settings()

        self.transport = transport
        self.sleep = sleep

        self.timeout = settings.binance_request_timeout_seconds
        self.max_retries = settings.exchange_max_retries
        self.retry_base = settings.exchange_retry_base_seconds
        self.retry_max = settings.exchange_retry_max_seconds

    def _retry_delay(
        self,
        attempt: int,
        error: ExchangeError,
    ) -> float:
        exponential_delay = min(
            self.retry_base * (2 ** attempt),
            self.retry_max,
        )

        if isinstance(error, ExchangeRateLimitError):
            if error.retry_after is not None:
                return max(exponential_delay, error.retry_after)

        return exponential_delay

    def _raise_for_response(
        self,
        response: httpx.Response,
    ) -> None:
        status = response.status_code

        if status in (418, 429):
            retry_after_header = response.headers.get(
                "Retry-After"
            )

            retry_after = None

            if retry_after_header:
                try:
                    retry_after = max(
                        0.0,
                        float(retry_after_header),
                    )
                except ValueError:
                    logger.warning(
                        "Invalid Retry-After header: %s",
                        retry_after_header,
                    )

            raise ExchangeRateLimitError(
                f"Binance rate limit: HTTP {status}",
                retry_after=retry_after,
            )

        if status >= 500:
            raise ExchangeUnavailableError(
                f"Binance server error: HTTP {status}"
            )

        if status >= 400:
            raise ExchangeAPIError(
                f"Binance returned HTTP {status}"
            )

    async def get_ticker_price(
        self,
        symbol: str,
    ) -> BinanceTickerPriceResponse:

        async with httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=self.timeout,
            transport=self.transport,
        ) as client:

            for attempt in range(self.max_retries + 1):

                try:
                    response = await client.get(
                        "/api/v3/ticker/price",
                        params={"symbol": symbol},
                    )

                    self._raise_for_response(response)

                    data = response.json()

                    return BinanceTickerPriceResponse.model_validate(
                        data
                    )

                except httpx.TimeoutException as exc:
                    error = ExchangeTimeoutError(
                        "Binance request timed out."
                    )
                    error.__cause__ = exc

                except httpx.RequestError as exc:
                    error = ExchangeConnectionError(
                        "Could not connect to Binance."
                    )
                    error.__cause__ = exc

                except ExchangeError as exc:
                    error = exc

                except (ValueError, ValidationError) as exc:
                    raise ExchangeResponseError(
                        "Binance returned an invalid response."
                    ) from exc

                retryable = isinstance(
                    error,
                    (
                        ExchangeTimeoutError,
                        ExchangeConnectionError,
                        ExchangeRateLimitError,
                        ExchangeUnavailableError,
                    ),
                )

                if not retryable or attempt >= self.max_retries:
                    raise error

                delay = self._retry_delay(attempt, error)

                logger.warning(
                    "Binance request failed for %s. "
                    "Retry %s/%s in %.2f seconds. Error: %s",
                    symbol,
                    attempt + 1,
                    self.max_retries,
                    delay,
                    error,
                )

                await self.sleep(delay)

        raise RuntimeError("Unexpected Binance retry loop exit.")