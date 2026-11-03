import httpx
from pydantic import ValidationError

from app.exchanges.binance.schemas import BinanceTickerPriceResponse
from app.exchanges.exceptions import (
    ExchangeAPIError,
    ExchangeConnectionError,
    ExchangeRateLimitError,
    ExchangeResponseError,
    ExchangeTimeoutError,
    ExchangeUnavailableError,
)


class BinanceClient:

    BASE_URL = "https://api.binance.com"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self.transport = transport

    async def get_ticker_price(
        self,
        symbol: str
    ) -> BinanceTickerPriceResponse:

        try:
            async with httpx.AsyncClient(
                base_url=self.BASE_URL,
                timeout=10.0,
                transport=self.transport
            ) as client:

                response = await client.get(
                    "/api/v3/ticker/price",
                    params={"symbol": symbol}
                )

                response.raise_for_status()

                data = response.json()

                return BinanceTickerPriceResponse.model_validate(data)

        except httpx.TimeoutException as exc:
            raise ExchangeTimeoutError(
                "Binance request timed out."
            ) from exc

        except httpx.HTTPStatusError as exc:

            status_code = exc.response.status_code

            if status_code == 429:
                raise ExchangeRateLimitError(
                    "Binance rate limit exceeded."
                ) from exc

            if status_code >= 500:
                raise ExchangeUnavailableError(
                    f"Binance server error: HTTP {status_code}"
                ) from exc

            raise ExchangeAPIError(
                f"Binance returned HTTP {status_code}"
            ) from exc

        except httpx.RequestError as exc:
            raise ExchangeConnectionError(
                "Could not connect to Binance."
            ) from exc

        except (ValueError, ValidationError) as exc:
            raise ExchangeResponseError(
                "Binance returned an invalid response."
            ) from exc