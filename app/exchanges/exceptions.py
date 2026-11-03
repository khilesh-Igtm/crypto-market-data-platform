class ExchangeError(Exception):
    """Base exception for exchange-related errors."""


class ExchangeTimeoutError(ExchangeError):
    """Exchange request timed out."""


class ExchangeConnectionError(ExchangeError):
    """Could not connect to the exchange."""


class ExchangeRateLimitError(ExchangeError):
    """Exchange rate limit exceeded."""


class ExchangeUnavailableError(ExchangeError):
    """Exchange server is unavailable."""


class ExchangeAPIError(ExchangeError):
    """Exchange returned an unsuccessful HTTP response."""


class ExchangeResponseError(ExchangeError):
    """Exchange returned an invalid or unexpected response."""