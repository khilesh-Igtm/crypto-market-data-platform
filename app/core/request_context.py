from contextvars import ContextVar

request_id_context: ContextVar[str] = ContextVar(
    "request_id",
    default="-",
)


class RequestIdFilter:
    def filter(self, record):
        record.request_id = request_id_context.get()
        return True