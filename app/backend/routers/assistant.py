from __future__ import annotations

import json
import uuid
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.backend.response import success_response
from app.backend.schemas import (
	ApiEnvelope,
	AssistantRespondRequest,
	AssistantRespondV2Request,
	AssistantStreamRequest,
	AssistantStreamV2Request,
)
from app.backend.services import assistant_service


router = APIRouter(prefix="/api/assistant", tags=["assistant"])


def _session_id_from_request(request: Request) -> str:
	session_id = request.headers.get("X-Session-ID", "").strip()
	return session_id or uuid.uuid4().hex


def _trace_enabled(request: Request) -> bool:
	return request.headers.get("X-ACA-Trace", "").strip() == "1"


def _trace_requested(request: Request, payload_trace: bool) -> bool:
	return _trace_enabled(request) or payload_trace


def _encode_sse(event: str, data: dict) -> str:
	payload = json.dumps(data, ensure_ascii=False)
	return f"event: {event}\ndata: {payload}\n\n"


@router.get("/models", response_model=ApiEnvelope)
def models(request: Request):
	try:
		catalog = assistant_service.list_models()
	except assistant_service.AssistantServiceError as exc:
		raise HTTPException(
			status_code=exc.status_code,
			detail={"code": exc.code, "message": exc.message},
		) from exc
	return success_response(
		request=request,
		data={
			"models": catalog["models"],
			"default_model": catalog["default_model"],
			"provider_mode": catalog["provider_mode"],
		},
	)


@router.post("/respond", response_model=ApiEnvelope)
def respond(request: Request, payload: AssistantRespondRequest):
	session_id = _session_id_from_request(request)
	trace_enabled = _trace_requested(request, False)
	try:
		result, trace = assistant_service.respond_with_trace(
			user_input=payload.user_input,
			context=payload.context,
			risk_tolerance=payload.risk_tolerance,
			max_questions=payload.max_questions,
			model=payload.model,
			session_id=session_id,
			trace_enabled=trace_enabled,
		)
	except assistant_service.AssistantServiceError as exc:
		raise HTTPException(
			status_code=exc.status_code,
			detail={"code": exc.code, "message": exc.message},
		) from exc
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc

	data = {"assistant": result, "session_id": session_id}
	if trace_enabled:
		data["aca_trace"] = trace
	return success_response(request=request, data=data)


@router.post("/respond-v2", response_model=ApiEnvelope)
def respond_v2(request: Request, payload: AssistantRespondV2Request):
	session_id = _session_id_from_request(request)
	trace_enabled = _trace_requested(request, payload.trace)
	try:
		result, _trace = assistant_service.respond_v2_with_trace(
			user_input=payload.user_input,
			context=payload.context,
			risk_tolerance=payload.risk_tolerance,
			max_questions=payload.max_questions,
			model=payload.model,
			session_id=session_id,
			trace_enabled=trace_enabled,
		)
	except assistant_service.AssistantServiceError as exc:
		raise HTTPException(
			status_code=exc.status_code,
			detail={"code": exc.code, "message": exc.message},
		) from exc
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc
	return success_response(request=request, data=result)


@router.post("/stream")
def stream(request: Request, payload: AssistantStreamRequest):
	session_id = _session_id_from_request(request)
	trace_enabled = _trace_requested(request, False)

	def generate() -> Iterator[str]:
		try:
			for event in assistant_service.stream_respond(
				user_input=payload.user_input,
				context=payload.context,
				risk_tolerance=payload.risk_tolerance,
				max_questions=payload.max_questions,
				model=payload.model,
				session_id=session_id,
				trace_enabled=trace_enabled,
			):
				event_name = str(event.get("event") or "message")
				data = event.get("data")
				if not isinstance(data, dict):
					data = {"value": data}
				yield _encode_sse(event_name, data)
		except assistant_service.AssistantServiceError as exc:
			yield _encode_sse("error", {"code": exc.code, "message": exc.message})
		except ValueError as exc:
			yield _encode_sse("error", {"code": "assistant_bad_request", "message": str(exc)})
		except Exception:
			yield _encode_sse(
				"error",
				{"code": "assistant_provider_error", "message": "Assistant stream failed."},
			)

	return StreamingResponse(
		generate(),
		media_type="text/event-stream",
		headers={
			"Cache-Control": "no-cache",
			"Connection": "keep-alive",
			"X-Accel-Buffering": "no",
		},
	)


@router.post("/stream-v2")
def stream_v2(request: Request, payload: AssistantStreamV2Request):
	session_id = _session_id_from_request(request)
	trace_enabled = _trace_requested(request, payload.trace)

	def generate() -> Iterator[str]:
		try:
			for event in assistant_service.stream_v2(
				user_input=payload.user_input,
				context=payload.context,
				risk_tolerance=payload.risk_tolerance,
				max_questions=payload.max_questions,
				model=payload.model,
				session_id=session_id,
				trace_enabled=trace_enabled,
			):
				event_name = str(event.get("event") or "message")
				data = event.get("data")
				if not isinstance(data, dict):
					data = {"value": data}
				yield _encode_sse(event_name, data)
		except assistant_service.AssistantServiceError as exc:
			yield _encode_sse("error", {"code": exc.code, "message": exc.message})
		except ValueError as exc:
			yield _encode_sse("error", {"code": "assistant_bad_request", "message": str(exc)})
		except Exception:
			yield _encode_sse(
				"error",
				{"code": "assistant_provider_error", "message": "Assistant stream failed."},
			)

	return StreamingResponse(
		generate(),
		media_type="text/event-stream",
		headers={
			"Cache-Control": "no-cache",
			"Connection": "keep-alive",
			"X-Accel-Buffering": "no",
		},
	)
