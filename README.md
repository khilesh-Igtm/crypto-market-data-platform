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