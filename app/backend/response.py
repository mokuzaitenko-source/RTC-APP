from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Request


def now_iso() -> str:
	return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _request_id(request: Optional[Request]) -> Optional[str]:
	if request is None:
		return None
	return getattr(request.state, "request_id", None)


def success_response(
	*,
	request: Optional[Request] = None,
	data: Optional[Dict[str, Any]] = None,
	report: Optional[Dict[str, Any]] = None,
	run_event: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
	payload: Dict[str, Any] = {
		"ok": True,
		"generated_at": now_iso(),
	}
	request_id = _request_id(request)
	if request_id:
		payload["request_id"] = request_id
	if data is not None:
		payload["data"] = data
	if report is not None:
		payload["report"] = report
	if run_event is not None:
		payload["run_event"] = run_event
	return payload


def error_response(
	*,
	code: str,
	message: str,
	request: Optional[Request] = None,
	evidence: Optional[List[str]] = None,
) -> Dict[str, Any]:
	payload: Dict[str, Any] = {
		"ok": False,
		"generated_at": now_iso(),
		"error": {
			"code": code,
			"message": message,
			"evidence": evidence or [],
		},
	}
	request_id = _request_id(request)
	if request_id:
		payload["request_id"] = request_id
	return payload
