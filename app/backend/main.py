from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.backend import constants
from app.backend.middleware import RequestContextMiddleware
from app.backend.response import error_response
from app.backend.routers import assistant

_FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


def create_app() -> FastAPI:
	app = FastAPI(
		title=constants.APP_NAME,
		version=constants.APP_VERSION,
	)
	_register_middleware(app)
	_register_handlers(app)
	_register_routers(app)
	return app


def _register_middleware(app: FastAPI) -> None:
	app.add_middleware(RequestContextMiddleware)
	app.add_middleware(GZipMiddleware, minimum_size=1024)
	app.add_middleware(
		CORSMiddleware,
		allow_origins=constants.DEFAULT_CORS_ALLOW_ORIGINS,
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)
	app.add_middleware(
		TrustedHostMiddleware,
		allowed_hosts=constants.DEFAULT_TRUSTED_HOSTS,
	)


def _register_routers(app: FastAPI) -> None:
	if _FRONTEND_DIR.exists():
		app.mount("/app", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")

		@app.get("/", include_in_schema=False)
		def serve_root():
			return RedirectResponse(url="/app")

		@app.get("/learn", include_in_schema=False)
		def serve_learn():
			return RedirectResponse(url="/app")

	app.include_router(assistant.router)


def _register_handlers(app: FastAPI) -> None:
	@app.exception_handler(HTTPException)
	async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
		code = f"http_{exc.status_code}"
		message = _exc_message(exc.detail)
		evidence = None
		if isinstance(exc.detail, dict):
			detail_code = exc.detail.get("code")
			detail_message = exc.detail.get("message")
			detail_evidence = exc.detail.get("evidence")
			if isinstance(detail_code, str) and detail_code.strip():
				code = detail_code.strip()
			if isinstance(detail_message, str) and detail_message.strip():
				message = detail_message.strip()
			if isinstance(detail_evidence, list):
				evidence = [str(item) for item in detail_evidence]
		payload = error_response(
			code=code,
			message=message,
			request=request,
			evidence=evidence,
		)
		return JSONResponse(status_code=exc.status_code, content=payload)

	@app.exception_handler(StarletteHTTPException)
	async def handle_starlette_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
		payload = error_response(
			code=f"http_{exc.status_code}",
			message=_exc_message(exc.detail),
			request=request,
		)
		return JSONResponse(status_code=exc.status_code, content=payload)

	@app.exception_handler(RequestValidationError)
	async def handle_request_validation_error(
		request: Request,
		exc: RequestValidationError,
	) -> JSONResponse:
		evidence = []
		for issue in exc.errors():
			loc = ".".join(str(part) for part in issue.get("loc", []))
			msg = issue.get("msg", "Invalid request.")
			evidence.append(f"{loc}: {msg}" if loc else msg)
		payload = error_response(
			code="validation_error",
			message="Request validation failed.",
			request=request,
			evidence=evidence,
		)
		return JSONResponse(status_code=422, content=payload)

	@app.exception_handler(Exception)
	async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
		payload = error_response(
			code="internal_error",
			message="Internal server error.",
			request=request,
		)
		return JSONResponse(status_code=500, content=payload)


def _exc_message(detail: Any) -> str:
	if isinstance(detail, str):
		return detail
	if detail is None:
		return "Request failed."
	return str(detail)


app = create_app()
