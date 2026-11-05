import json
import logging

from app.core.logging import JsonFormatter


def test_json_formatter():
    formatter = JsonFormatter()

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="production test",
        args=(),
        exc_info=None,
    )

    result = json.loads(formatter.format(record))

    assert result["level"] == "INFO"
    assert result["message"] == "production test"
    assert result["logger"] == "test"
    assert "timestamp" in result


def test_json_formatter_includes_exception():
    try:
        raise ValueError("test error")
    except ValueError:
        import sys
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="test.py",
        lineno=1,
        msg="failed",
        args=(),
        exc_info=exc_info,
    )

    result = json.loads(JsonFormatter().format(record))

    assert "exception" in result
    assert "ValueError" in result["exception"]