from decimal import Decimal

import httpx
import pytest

from app.exchanges.binance.client import BinanceClient
from app.exchanges.exceptions import (
    ExchangeAPIError,
    ExchangeConnectionError,
    ExchangeRateLimitError,
    ExchangeResponseError,
    ExchangeTimeoutError,
    ExchangeUnavailableError,
)


# Ye fixture ek fake client banata hai bina asli internet use kiye
@pytest.fixture
def client_factory():
    async def no_sleep(delay):
        return None

    def create_client(handler):
        transport = httpx.MockTransport(handler)

        return BinanceClient(
            transport=transport,
            sleep=no_sleep,
        )

    return create_client

# Test 1: Successful response (Happy Path)
async def test_get_ticker_price(client_factory):
    def handler(request):
        assert request.url.path == "/api/v3/ticker/price"
        assert request.url.params["symbol"] == "BTCUSDT"
        return httpx.Response(
            200,
            json={"symbol": "BTCUSDT", "price": "77236.01000000"},
            request=request)
    
    client = client_factory(handler)
    response = await client.get_ticker_price("BTCUSDT")
    
    assert response.symbol == "BTCUSDT"
    assert response.price == Decimal("77236.01000000")
    assert isinstance(response.price, Decimal)

# Test 2: Multiple HTTP Errors (400, 429, 500)
@pytest.mark.parametrize("status_code, expected_exception", [
    (400, ExchangeAPIError),
    (429, ExchangeRateLimitError),
    (500, ExchangeUnavailableError),
])
async def test_http_errors(client_factory, status_code, expected_exception):
    def handler(request):
        return httpx.Response(status_code, 
        json={"error": "Something went wrong"}, 
        request=request)
    
    client = client_factory(handler)
    with pytest.raises(expected_exception):
        await client.get_ticker_price("BTCUSDT")

# Test 3: Timeout Error
async def test_timeout_error(client_factory):
    def handler(request):
        raise httpx.ReadTimeout("Request timed out", request=request)
    
    client = client_factory(handler)
    with pytest.raises(ExchangeTimeoutError):
        await client.get_ticker_price("BTCUSDT")

# Test 4: Invalid JSON/Data Error
async def test_invalid_response(client_factory):
    def handler(request):
        return httpx.Response(200, 
        json={"symbol": "BTCUSDT", "price": "invalid"}, 
        request=request)
    
    client = client_factory(handler)
    with pytest.raises(ExchangeResponseError):
        await client.get_ticker_price("BTCUSDT")

# Test 5: Connection Failure (ChatGPT's Extra Challenge)
async def test_connection_error(client_factory):
    def handler(request):
        raise httpx.ConnectError("Connection failed", request=request)
    
    client = client_factory(handler)
    with pytest.raises(ExchangeConnectionError):
        await client.get_ticker_price("BTCUSDT")

async def test_retries_transient_server_error(client_factory):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1

        if calls < 3:
            return httpx.Response(
                503,
                request=request,
            )

        return httpx.Response(
            200,
            json={
                "symbol": "BTCUSDT",
                "price": "70000.00",
            },
            request=request,
        )

    client = client_factory(handler)

    response = await client.get_ticker_price("BTCUSDT")

    assert response.symbol == "BTCUSDT"
    assert response.price == Decimal("70000.00")
    assert calls == 3


async def test_retry_after_header_is_respected():
    delays = []
    calls = 0

    async def fake_sleep(delay):
        delays.append(delay)

    def handler(request):
        nonlocal calls
        calls += 1

        if calls == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "2"},
                request=request,
            )

        return httpx.Response(
            200,
            json={
                "symbol": "BTCUSDT",
                "price": "70000.00",
            },
            request=request,
        )

    client = BinanceClient(
        transport=httpx.MockTransport(handler),
        sleep=fake_sleep,
    )

    response = await client.get_ticker_price("BTCUSDT")

    assert response.symbol == "BTCUSDT"
    assert calls == 2
    assert delays == [2.0]


async def test_no_retry_for_bad_request():
    calls = 0

    async def fake_sleep(delay):
        raise AssertionError("400 errors must not be retried")

    def handler(request):
        nonlocal calls
        calls += 1

        return httpx.Response(
            400,
            request=request,
        )

    client = BinanceClient(
        transport=httpx.MockTransport(handler),
        sleep=fake_sleep,
    )

    with pytest.raises(ExchangeAPIError):
        await client.get_ticker_price("INVALID")

    assert calls == 1