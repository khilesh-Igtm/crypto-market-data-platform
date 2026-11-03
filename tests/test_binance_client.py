import httpx
import pytest
from decimal import Decimal
from app.exchanges.binance.client import BinanceClient
from app.exchanges.exceptions import (
    ExchangeAPIError, ExchangeRateLimitError, ExchangeUnavailableError,
    ExchangeTimeoutError, ExchangeResponseError, ExchangeConnectionError
)

# Ye fixture ek fake client banata hai bina asli internet use kiye
@pytest.fixture
def client_factory():
    def create_client(handler):
        transport = httpx.MockTransport(handler)
        return BinanceClient(transport=transport)
    return create_client

# Test 1: Successful response (Happy Path)
async def test_get_ticker_price(client_factory):
    def handler(request):
        assert request.url.path == "/api/v3/ticker/price"
        assert request.url.params["symbol"] == "BTCUSDT"
        return httpx.Response(200, json={"symbol": "BTCUSDT", "price": "77236.01000000"}, request=request)
    
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
        return httpx.Response(status_code, json={"error": "Something went wrong"}, request=request)
    
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
        return httpx.Response(200, json={"symbol": "BTCUSDT", "price": "invalid"}, request=request)
    
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