# Crypto Market Data Platform

A production-oriented crypto market data platform
built with Python and FastAPI.

## Tech Stack

- Python 3.12+
- FastAPI
- Uvicorn
- Pydantic
- Pydantic Settings
- uv
- Pytest
- Ruff

## Setup

Install dependencies:

uv sync

Create local environment file:

Copy-Item .env.example .env

Run application:

uv run uvicorn app.main:app --reload

## API Documentation

http://127.0.0.1:8000/docs

## Health Check

GET /api/v1/health

## Testing

uv run pytest -v

## Code Quality

uv run ruff check .
uv run ruff format .


## Infrastructure

- PostgreSQL: Primary persistent database
- Redis: In-memory caching layer
- Docker Compose: Redis infrastructure

## Redis Setup

Start Redis:

    docker compose up -d redis

Check Redis:

    docker compose exec redis redis-cli ping

Expected output:

    PONG

## Caching Strategy

The application uses the cache-aside pattern.

1. Check Redis for requested market data.
2. Return cached data when available.
3. Query PostgreSQL on a cache miss.
4. Store the result in Redis with a TTL.

Default TTL configuration:

- Latest market price: 5 seconds
- Historical market data: 60 seconds

Redis failures fall back to PostgreSQL.

## Health Monitoring

- GET /api/v1/health
- GET /api/v1/health/database
- GET /api/v1/health/redis

## Redis Shutdown

    docker compose stop redis