import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.request_context import request_id_context

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next,
    ) -> Response:
        request_id = request.headers.get("X-Request-ID")

        if not request_id or len(request_id) > 128:
            request_id = str(uuid.uuid4())

        token = request_id_context.set(request_id)
        start_time = time.perf_counter()

        try:
            response = await call_next(request)

            duration = time.perf_counter() - start_time

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{duration:.6f}"

            logger.info(
                "HTTP request completed",
                extra={"request_id": request_id},
            )

            return response

        except Exception:
            logger.exception("HTTP request failed")
            raise

        finally:
            request_id_context.reset(token)