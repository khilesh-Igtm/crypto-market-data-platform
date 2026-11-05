from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

# from app.market_data import service
import app.api.routes.market_data as market_data_routes
from app.cache.dependencies import get_redis_cache
from app.db.session import get_db_session
from app.main import app


@pytest.fixture
def api_client():
    async def fake_db():
        class FakeResult:
            def scalar_one(self):
                return 1

        class FakeSession:
            async def execute(self, statement):
                return FakeResult()

        yield FakeSession()

    class FakeCache:
        async def get_json(self, key):
            return None

        async def set_json(self, key, value, ttl):
            return True

        async def delete(self, key):
            return True

        async def ping(self):
            return True

    app.dependency_overrides[get_db_session] = fake_db
    app.dependency_overrides[get_redis_cache] = lambda: FakeCache()

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def make_price(
    price=Decimal("70000.50"),
    symbol="BTCUSDT",
):
    return SimpleNamespace(
        id=1,
        exchange="binance",
        symbol=symbol,
        price=price,
        fetched_at=datetime.now(timezone.utc),
    )


def test_health_endpoint(api_client):
    response = api_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_latest_market_price_success(api_client, monkeypatch):
    async def fake_latest(**kwargs):
        return make_price()

    monkeypatch.setattr(
        market_data_routes,
        "get_latest_market_price",
        fake_latest,
    )

    response = api_client.get(
        "/api/v1/market-data/latest/BTCUSDT",
        params={"exchange": "binance"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["symbol"] == "BTCUSDT"
    assert data["exchange"] == "binance"
    assert Decimal(data["price"]) == Decimal("70000.50")


def test_latest_market_price_not_found(api_client, monkeypatch):
    async def fake_latest(**kwargs):
        return None

    monkeypatch.setattr(
        market_data_routes,
        "get_latest_market_price",
        fake_latest,
    )

    response = api_client.get(
        "/api/v1/market-data/latest/UNKNOWN",
        params={"exchange": "binance"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Market price not found"


def test_latest_market_price_missing_exchange(api_client):
    response = api_client.get(
        "/api/v1/market-data/latest/BTCUSDT"
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "symbol",
    ["A" * 31],
)
def test_latest_market_price_invalid_symbol(api_client, symbol):
    response = api_client.get(
        f"/api/v1/market-data/latest/{symbol}",
        params={"exchange": "binance"},
    )

    assert response.status_code == 422


def test_history_market_price_success(api_client, monkeypatch):
    async def fake_history(**kwargs):
        return [
            make_price(Decimal("71000")),
            make_price(Decimal("70000")),
        ]

    monkeypatch.setattr(
        market_data_routes,
        "get_market_price_history",
        fake_history,
    )

    response = api_client.get(
        "/api/v1/market-data/history/BTCUSDT",
        params={
            "exchange": "binance",
            "limit": 2,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["exchange"] == "binance"
    assert data["symbol"] == "BTCUSDT"
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert data["has_more"] is False
    assert len(data["prices"]) == 2


def test_history_has_more_records(api_client, monkeypatch):
    async def fake_history(**kwargs):
        # Route requests limit + 1 records to determine has_more.
        assert kwargs["limit"] == 3

        return [
            make_price(Decimal("73000")),
            make_price(Decimal("72000")),
            make_price(Decimal("71000")),
        ]

    monkeypatch.setattr(
        market_data_routes,
        "get_market_price_history",
        fake_history,
    )

    response = api_client.get(
        "/api/v1/market-data/history/BTCUSDT",
        params={
            "exchange": "binance",
            "limit": 2,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["prices"]) == 2
    assert data["has_more"] is True


@pytest.mark.parametrize(
    "params",
    [
        {"exchange": "binance", "limit": 0},
        {"exchange": "binance", "limit": 501},
        {"exchange": "binance", "offset": -1},
    ],
)
def test_history_invalid_pagination(api_client, params):
    response = api_client.get(
        "/api/v1/market-data/history/BTCUSDT",
        params=params,
    )

    assert response.status_code == 422


def test_history_invalid_time_range(api_client):
    response = api_client.get(
        "/api/v1/market-data/history/BTCUSDT",
        params={
            "exchange": "binance",
            "start_time": "2026-11-05T12:00:00Z",
            "end_time": "2026-11-04T12:00:00Z",
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "start_time must be earlier than or equal to end_time"
    )


def test_history_empty_result(api_client, monkeypatch):
    async def fake_history(**kwargs):
        return []

    monkeypatch.setattr(
        market_data_routes,
        "get_market_price_history",
        fake_history,
    )

    response = api_client.get(
        "/api/v1/market-data/history/BTCUSDT",
        params={"exchange": "binance"},
    )

    assert response.status_code == 200
    assert response.json()["prices"] == []
    assert response.json()["has_more"] is False



def test_database_health_success(api_client):
    response = api_client.get("/api/v1/health/database")

    assert response.status_code == 200
    assert response.json() == {
        "status": "database_connected"
    }


def test_database_health_failure(api_client):
    class BrokenSession:
        async def execute(self, statement):
            raise OperationalError(
                "SELECT 1",
                {},
                Exception("Database unavailable"),
            )

    async def failing_db():
        yield BrokenSession()

    app.dependency_overrides[get_db_session] = failing_db

    response = api_client.get("/api/v1/health/database")

    assert response.status_code == 503
    assert response.json()["detail"] == "Database is unavailable"


def test_redis_health_success(api_client):
    response = api_client.get("/api/v1/health/redis")

    assert response.status_code == 200
    assert response.json() == {
        "status": "redis_connected"
    }


def test_redis_health_failure(api_client):
    class BrokenCache:
        async def ping(self):
            return False

    app.dependency_overrides[get_redis_cache] = (
        lambda: BrokenCache()
    )

    response = api_client.get("/api/v1/health/redis")

    assert response.status_code == 503
    assert response.json()["detail"] == "Redis is unavailable"