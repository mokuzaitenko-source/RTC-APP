from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List

from app.backend.aca.types import ACATraceEvent, TraceStatus, TraceTier


def now_iso() -> str:
	return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def make_event(
	*,
	module_id: str,
	module_name: str,
	tier: TraceTier,
	status: TraceStatus,
	detail: str,
) -> ACATraceEvent:
	return ACATraceEvent(
		module_id=module_id,
		module_name=module_name,
		tier=tier,
		status=status,
		detail=detail,
		timestamp=now_iso(),
	)


def serialize_trace(trace_events: Iterable[ACATraceEvent]) -> List[dict]:
	return [event.as_dict() for event in trace_events]

