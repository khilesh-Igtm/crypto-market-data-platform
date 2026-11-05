import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.exceptions import register_exception_handlers


@pytest.fixture
def client():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/failure")
    async def failure():
        raise RuntimeError("internal secret")

    @app.get("/not-found")
    async def not_found():
        raise HTTPException(
            status_code=404,
            detail="Not found",
        )

    return TestClient(
        app,
        raise_server_exceptions=False,
    )


def test_unexpected_exception_is_hidden(client):
    response = client.get("/failure")

    assert response.status_code == 500

    assert response.json() == {
        "error": {
            "type": "internal_server_error",
            "message": "An unexpected error occurred",
        }
    }

    assert "internal secret" not in response.text


def test_http_exception_handler(client):
    response = client.get("/not-found")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Not found",
    }