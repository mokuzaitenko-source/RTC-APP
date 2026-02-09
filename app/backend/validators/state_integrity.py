from __future__ import annotations

from typing import List

from app.backend.adapters import sqlite_adapter
from .evidence import sort_evidence
from .playbook_parser import parse_findings
from .types import EvidenceItem, InvariantResult, ValidatorContext


_ALLOWED_STATUSES = {"unstarted", "in_progress", "blocked", "ready_for_validation"}


def check(ctx: ValidatorContext) -> InvariantResult:
	playbook_ids = {f.finding_id for f in parse_findings(ctx.playbook_path)}
	state_rows = sqlite_adapter.get_finding_states(ctx.state_db_path)
	unknown: List[str] = []
	invalid_status: List[str] = []
	for row in state_rows:
		finding_id = row.get("finding_id", "")
		status = row.get("status", "")
		if finding_id and finding_id not in playbook_ids:
			unknown.append(finding_id)
		if status and status not in _ALLOWED_STATUSES:
			invalid_status.append(f"{finding_id}:{status}")

	evidence_items: List[EvidenceItem] = []
	if unknown or invalid_status:
		evidence_items.append(
			EvidenceItem(
				kind="id_list",
				ref="state_integrity",
				detail=f"unknown={sorted(unknown)}; invalid_status={sorted(invalid_status)}",
			)
		)

	evidence = sort_evidence(evidence_items)
	if not unknown and not invalid_status:
		return InvariantResult(
			id="state_integrity",
			status="pass",
			message="App state references known findings and valid statuses.",
			evidence=evidence,
			recommended_action="",
		)

	return InvariantResult(
		id="state_integrity",
		status="fail",
		message="App state contains unknown findings or invalid statuses.",
		evidence=evidence,
		recommended_action="repair_state",
	)

