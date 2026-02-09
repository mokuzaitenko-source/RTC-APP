from __future__ import annotations

from fastapi import APIRouter, Request

from app.backend.response import success_response
from app.backend.schemas import ApiEnvelope
from app.backend.services import session_service


router = APIRouter(prefix="/api/session", tags=["session"])


@router.post("/start", response_model=ApiEnvelope)
def start_session(request: Request):
	data = session_service.start_session()
	return success_response(
		request=request,
		data=data,
	)
