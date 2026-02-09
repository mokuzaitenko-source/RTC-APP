from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, cast

from app.backend import constants
from app.backend.adapters import docs_adapter, process_adapter, sqlite_adapter
from app.backend.services import action_queue_service, health_service
from app.backend.validators.engine import run_all_validators
from app.backend.validators.types import InvariantResult, RunRecords, ValidatorContext, ValidatorReport


def _now_iso() -> str:
	return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_context(run_records: RunRecords) -> ValidatorContext:
	paths = docs_adapter.get_default_paths()
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


def run_sync() -> Dict[str, str]:
	run_id = str(uuid.uuid4())
	result = process_adapter.run_sync_process()
	exit_code = int(result["exit_code"])
	started_at = str(result["started_at"])
	ended_at = str(result["ended_at"])
	stdout = str(result["stdout"])
	stderr = str(result["stderr"])
	status = "pass" if exit_code == 0 else "fail"
	run_event = {
		"run_id": run_id,
		"run_type": "sync",
		"status": status,
		"started_at": started_at,
		"ended_at": ended_at,
		"stdout": stdout,
		"stderr": stderr,
		"summary": f"sync_exit_code={exit_code}",
	}
	sqlite_adapter.record_run_event(
		run_type="sync",
		exit_code=exit_code,
		started_at=started_at,
		ended_at=ended_at,
		stdout=stdout,
		stderr=stderr,
		db_path=constants.DEFAULT_DB_PATH,
	)
	return run_event


def run_validate() -> Tuple[ValidatorReport, Dict[str, str], ValidatorContext]:
	run_id = str(uuid.uuid4())
	last_records = sqlite_adapter.get_latest_run_records(constants.DEFAULT_DB_PATH)
	run_records = RunRecords(
		sync_exit_code=last_records.sync_exit_code,
		validate_exit_code=0,
	)
	ctx = _build_context(run_records)
	started_at = _now_iso()
	report = run_all_validators(ctx)
	ended_at = _now_iso()
	status = "pass" if report.status == "pass" else "fail"
	run_event = {
		"run_id": run_id,
		"run_type": "validate",
		"status": status,
		"started_at": started_at,
		"ended_at": ended_at,
		"stdout": "",
		"stderr": "",
		"summary": report.summary,
	}
	sqlite_adapter.record_run_event(
		run_type="validate",
		# Exit code represents validator process execution, not invariant status.
		exit_code=0,
		started_at=started_at,
		ended_at=ended_at,
		stdout="",
		stderr="",
		db_path=constants.DEFAULT_DB_PATH,
	)
	return report, run_event, ctx


def start_session() -> Dict[str, object]:
	run_events: List[Dict[str, str]] = []
	run_events.append(run_sync())
	report, validate_event, ctx = run_validate()
	run_events.append(validate_event)
	actions = action_queue_service.build_action_queue(report, ctx)
	return {
		"run_events": run_events,
		"invariants": [_serialize_invariant(inv) for inv in report.invariants],
		"top_actions": actions,
	}


def export_status() -> str:
	summary = health_service.get_summary()
	parity = cast(Dict[str, Any], summary.get("parity", {}))
	coverage = cast(Dict[str, Any], summary.get("coverage", {}))
	blockers = cast(Dict[str, Any], summary.get("blockers", {}))
	wave1 = cast(List[str], blockers.get("wave1", []))
	unresolved = cast(List[str], blockers.get("unresolved", []))
	lines = [
		"# Oversight Ops Status",
		"",
		f"- Parity: rfc={parity['rfc_normative_count']}, matrix={parity['matrix_core_count']}",
		f"- Coverage: covered={coverage['covered']}, partial={coverage['partial']}, gap={coverage['gap']}",
		f"- Wave-1 blockers: {', '.join(wave1)}",
		f"- Unresolved blockers: {', '.join(unresolved)}",
	]
	return "\n".join(lines)


def _serialize_invariant(inv: InvariantResult) -> Dict[str, object]:
	return {
		"id": inv.id,
		"status": inv.status,
		"message": inv.message,
		"evidence": [
			{"kind": ev.kind, "ref": ev.ref, "detail": ev.detail, "hash": ev.hash}
			for ev in inv.evidence
		],
		"recommended_action": inv.recommended_action,
		"suggested_matches": inv.suggested_matches or [],
	}
