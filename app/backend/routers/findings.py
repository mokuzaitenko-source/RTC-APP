from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from app.backend.response import success_response
from app.backend.schemas import ApiEnvelope, FindingStateUpdate
from app.backend.services import state_service


router = APIRouter(prefix="/api/findings", tags=["findings"])


@router.get("", response_model=ApiEnvelope)
def list_findings(
	request: Request,
	finding_id: Optional[str] = None,
	wave: Optional[int] = None,
	is_blocker: Optional[bool] = None,
	status: Optional[str] = None,
):
	findings = state_service.list_findings(
		finding_id=finding_id,
		wave=wave,
		is_blocker=is_blocker,
		status=status,
	)
	return success_response(
		request=request,
		data={"findings": findings},
	)


@router.get("/{finding_id}", response_model=ApiEnvelope)
def get_finding(request: Request, finding_id: str):
	finding = state_service.get_finding(finding_id)
	if finding is None:
		raise HTTPException(status_code=404, detail="Finding not found.")
	return success_response(
		request=request,
		data={"finding": finding},
	)


@router.patch("/{finding_id}/state", response_model=ApiEnvelope)
def update_finding_state(request: Request, finding_id: str, payload: FindingStateUpdate):
	try:
		state = state_service.update_finding_state(
			finding_id=finding_id,
			status=payload.status,
			note=payload.note,
		)
	except LookupError as exc:
		raise HTTPException(status_code=404, detail=str(exc)) from exc
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc

	return success_response(
		request=request,
		data={"state": state},
	)
