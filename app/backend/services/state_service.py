from __future__ import annotations

from typing import Dict, List, Optional

from app.backend import constants
from app.backend.adapters import sqlite_adapter
from app.backend.validators.matrix_parser import parse_core_rows
from app.backend.validators.playbook_parser import parse_findings
from app.backend.validators.rfc_normative import extract_normative_lines


_ALLOWED_STATUSES = {"unstarted", "in_progress", "blocked", "ready_for_validation"}
_TRANSITIONS = {
	"unstarted": {"in_progress", "blocked"},
	"in_progress": {"blocked", "ready_for_validation"},
	"blocked": {"in_progress"},
	"ready_for_validation": {"in_progress"},
}


def _state_map() -> Dict[str, Dict[str, str]]:
	rows = sqlite_adapter.list_finding_states(db_path=constants.DEFAULT_DB_PATH)
	return {row["finding_id"]: row for row in rows}


def _finding_models() -> List[Dict[str, object]]:
	findings = parse_findings(constants.DEFAULT_PLAYBOOK_PATH)
	state_map = _state_map()
	models: List[Dict[str, object]] = []
	for finding in findings:
		state = state_map.get(finding.finding_id)
		status = state["status"] if state else "unstarted"
		models.append(
			{
				"finding_id": finding.finding_id,
				"is_wave1_blocker": finding.is_wave1_blocker,
				"dependencies": sorted(finding.dependencies),
				"impacted_req_ids": sorted(finding.impacted_req_ids),
				"impact_count": len(set(finding.impacted_req_ids)),
				"app_status": status,
				"proof_expectations": [],
				"source_refs": [],
			}
		)
	return models


def list_findings(
	finding_id: Optional[str] = None,
	wave: Optional[int] = None,
	is_blocker: Optional[bool] = None,
	status: Optional[str] = None,
) -> List[Dict[str, object]]:
	findings = _finding_models()
	filtered = []
	for finding in findings:
		if finding_id and finding["finding_id"] != finding_id:
			continue
		if wave is not None:
			if wave == 1 and not finding["is_wave1_blocker"]:
				continue
			if wave == 2 and finding["is_wave1_blocker"]:
				continue
		if is_blocker is not None and finding["is_wave1_blocker"] != is_blocker:
			continue
		if status and finding["app_status"] != status:
			continue
		filtered.append(finding)
	return filtered


def get_finding(finding_id: str) -> Optional[Dict[str, object]]:
	results = list_findings(finding_id=finding_id)
	return results[0] if results else None


def update_finding_state(
	finding_id: str,
	status: str,
	note: Optional[str],
) -> Dict[str, object]:
	if get_finding(finding_id) is None:
		raise LookupError("Finding not found.")
	current = sqlite_adapter.get_finding_state(finding_id, db_path=constants.DEFAULT_DB_PATH)
	current_status = current["status"] if current else "unstarted"
	if status not in _ALLOWED_STATUSES:
		raise ValueError("Invalid status value.")
	if status not in _TRANSITIONS.get(current_status, set()):
		raise ValueError("Illegal state transition.")
	return sqlite_adapter.upsert_finding_state(
		finding_id=finding_id,
		status=status,
		note=note,
		db_path=constants.DEFAULT_DB_PATH,
	)


def list_requirements(
	req_id: Optional[str] = None,
	status: Optional[str] = None,
	finding: Optional[str] = None,
	section: Optional[str] = None,
) -> List[Dict[str, object]]:
	rows = parse_core_rows(constants.DEFAULT_MATRIX_PATH)
	rfc_lines = extract_normative_lines(constants.DEFAULT_RFC_PATH)
	normative_map = {line.rfc_line_id: line.normative_level for line in rfc_lines}
	requirements: List[Dict[str, object]] = []
	for row in rows:
		if req_id and row.req_id != req_id:
			continue
		if status and row.status != status:
			continue
		if finding and finding not in row.findings:
			continue
		if section and not row.source_ref.startswith(f"RFC {section}:"):
			continue
		requirements.append(
			{
				"req_id": row.req_id,
				"status": row.status,
				"normative_level": normative_map.get(row.source_ref, ""),
				"enforcement_tbd": row.enforcement_tbd,
				"proof_tbd": row.proof_tbd,
				"linked_findings": row.findings,
				"source_ref": row.source_ref,
			}
		)
	return requirements
