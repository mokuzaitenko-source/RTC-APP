from __future__ import annotations

from fastapi import APIRouter, Request

from app.backend.response import success_response
from app.backend.schemas import ApiEnvelope
from app.backend.services import session_service


router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/status", response_model=ApiEnvelope)
def export_status(request: Request):
	markdown = session_service.export_status()
	return success_response(
		request=request,
		data={"markdown": markdown},
	)
