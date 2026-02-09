from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request

from app.backend.response import success_response
from app.backend.schemas import ApiEnvelope
from app.backend.services import state_service


router = APIRouter(prefix="/api/requirements", tags=["requirements"])


@router.get("", response_model=ApiEnvelope)
def list_requirements(
	request: Request,
	req_id: Optional[str] = None,
	status: Optional[str] = None,
	finding: Optional[str] = None,
	section: Optional[str] = None,
):
	requirements = state_service.list_requirements(
		req_id=req_id,
		status=status,
		finding=finding,
		section=section,
	)
	return success_response(
		request=request,
		data={"requirements": requirements},
	)
