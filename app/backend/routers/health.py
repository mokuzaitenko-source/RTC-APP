from __future__ import annotations

from fastapi import APIRouter, Request

from app.backend.response import success_response
from app.backend.schemas import ApiEnvelope
from app.backend.services import health_service


router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/summary", response_model=ApiEnvelope)
def get_summary(request: Request):
	data = health_service.get_summary()
	return success_response(
		request=request,
		data=data,
	)
