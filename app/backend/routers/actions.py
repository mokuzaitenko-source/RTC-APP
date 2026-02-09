from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request

from app.backend import constants
from app.backend.adapters import docs_adapter, sqlite_adapter
from app.backend.response import success_response
from app.backend.schemas import ApiEnvelope
from app.backend.services import action_queue_service
from app.backend.validators.engine import run_all_validators
from app.backend.validators.types import ValidatorContext


router = APIRouter(prefix="/api/actions", tags=["actions"])


def _build_context() -> ValidatorContext:
	paths = docs_adapter.get_default_paths()
	run_records = sqlite_adapter.get_latest_run_records(constants.DEFAULT_DB_PATH)
	return ValidatorContext(
		rfc_path=paths.rfc_path,
		matrix_path=paths.matrix_path,
		playbook_path=paths.playbook_path,
		handoff_path=paths.handoff_path,
		run_records=run_records,
		workspace_root=".",
		orphan_mapping_mode="source_line",
		state_db_path=constants.DEFAULT_DB_PATH,
	)


@router.get("/next", response_model=ApiEnvelope)
def get_next_actions(request: Request, limit: Optional[int] = 10):
	ctx = _build_context()
	report = run_all_validators(ctx)
	actions = action_queue_service.build_action_queue(report, ctx)
	if limit is not None:
		actions = actions[: max(limit, 0)]
	return success_response(
		request=request,
		data={"actions": actions},
	)
