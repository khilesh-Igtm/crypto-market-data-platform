import asyncio

from app.exchanges.binance.client import BinanceClient
from app.exchanges.exceptions import ExchangeError


async def main():

    client = BinanceClient()

    # Test 1: Valid request
    try:
        response = await client.get_ticker_price("BTCUSDT")
        print("BTC Price:", response.price)

    except ExchangeError as exc:
        print("Exchange Error:", exc)

    # Test 2: Invalid trading pair
    try:
        response = await client.get_ticker_price("INVALIDPAIR")
        print("Price:", response.price)

    except ExchangeError as exc:
        print("Expected Error:", type(exc).__name__)
        print("Error Message:", exc)


if __name__ == "__main__":
    asyncio.run(main())