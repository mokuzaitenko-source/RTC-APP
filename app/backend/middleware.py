from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestContextMiddleware(BaseHTTPMiddleware):
	async def dispatch(self, request: Request, call_next) -> Response:
		request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
		request.state.request_id = request_id
		start = time.perf_counter()
		response = await call_next(request)
		process_time = time.perf_counter() - start
		response.headers["X-Request-ID"] = request_id
		response.headers["X-Process-Time"] = f"{process_time:.6f}"
		return response
