from __future__ import annotations

from typing import Dict, List, Set

from .evidence import sort_evidence
from .matrix_parser import parse_core_rows
from .playbook_parser import parse_findings
from .types import EvidenceItem, InvariantResult, ValidatorContext


def _build_matrix_map(ctx: ValidatorContext) -> Dict[str, Set[str]]:
	rows = parse_core_rows(ctx.matrix_path)
	mapping: Dict[str, Set[str]] = {}
	for row in rows:
		for finding_id in row.findings:
			mapping.setdefault(finding_id, set()).add(row.req_id)
	return mapping


def _build_playbook_map(ctx: ValidatorContext) -> Dict[str, Set[str]]:
	findings = parse_findings(ctx.playbook_path)
	mapping: Dict[str, Set[str]] = {}
	for finding in findings:
		mapping[finding.finding_id] = set(finding.impacted_req_ids)
	return mapping


def check(ctx: ValidatorContext) -> InvariantResult:
	matrix_map = _build_matrix_map(ctx)
	playbook_map = _build_playbook_map(ctx)
	all_findings = sorted(set(matrix_map.keys()) | set(playbook_map.keys()))
	evidence_items: List[EvidenceItem] = []
	mismatched: List[str] = []
	for finding_id in all_findings:
		matrix_set = matrix_map.get(finding_id, set())
		playbook_set = playbook_map.get(finding_id, set())
		missing = sorted(playbook_set - matrix_set)
		extra = sorted(matrix_set - playbook_set)
		if missing or extra:
			mismatched.append(finding_id)
			evidence_items.append(
				EvidenceItem(
					kind="diff",
					ref=finding_id,
					detail=f"missing={missing}; extra={extra}",
				)
			)

	if mismatched:
		evidence_items.append(
			EvidenceItem(
				kind="id_list",
				ref="backlink_mismatch",
				detail=f"missing={sorted(mismatched)}; extra=[]",
			)
		)

	evidence = sort_evidence(evidence_items)
	if not mismatched:
		return InvariantResult(
			id="backlink_consistency",
			status="pass",
			message="Matrix backlinks match playbook impacted requirements.",
			evidence=evidence,
			recommended_action="",
		)

	return InvariantResult(
		id="backlink_consistency",
		status="fail",
		message="Matrix backlinks do not match playbook impacted requirements.",
		evidence=evidence,
		recommended_action="fix_backlinks",
	)

