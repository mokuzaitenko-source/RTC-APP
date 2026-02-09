from __future__ import annotations

from fastapi import APIRouter, Request

from app.backend.response import success_response
from app.backend.schemas import ApiEnvelope
from app.backend.services import session_service
from app.backend.validators.types import ValidatorReport


router = APIRouter(prefix="/api/ops", tags=["ops"])


@router.post("/run-validate", response_model=ApiEnvelope)
def run_validate(request: Request):
	report, _run_event, _ctx = session_service.run_validate()
	return success_response(
		request=request,
		report=_serialize_report(report),
	)


@router.post("/run-sync", response_model=ApiEnvelope)
def run_sync(request: Request):
	run_event = session_service.run_sync()
	return success_response(
		request=request,
		run_event=run_event,
	)


def _serialize_report(report: ValidatorReport) -> dict:
	return {
		"run_id": report.run_id,
		"run_type": report.run_type,
		"status": report.status,
		"started_at": report.started_at.isoformat().replace("+00:00", "Z"),
		"ended_at": report.ended_at.isoformat().replace("+00:00", "Z"),
		"invariants": [
			{
				"id": inv.id,
				"status": inv.status,
				"message": inv.message,
				"evidence": [
					{
						"kind": ev.kind,
						"ref": ev.ref,
						"detail": ev.detail,
						"hash": ev.hash,
					}
					for ev in inv.evidence
				],
				"recommended_action": inv.recommended_action,
				"suggested_matches": inv.suggested_matches or [],
			}
			for inv in report.invariants
		],
		"summary": report.summary,
	}
