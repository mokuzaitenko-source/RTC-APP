# app/backend/validators/finding_integrity.py
from __future__ import annotations

from .evidence import sort_evidence
from .matrix_parser import parse_core_rows
from .types import EvidenceItem, InvariantResult, ValidatorContext


def check(ctx: ValidatorContext) -> InvariantResult:
	rows = parse_core_rows(ctx.matrix_path)
	missing = [row.req_id for row in rows if row.status in {"gap", "partial"} and not row.findings]
	missing_sorted = sorted(missing)
	evidence = []
	if missing_sorted:
		evidence.append(
			EvidenceItem(
				kind="id_list",
				ref="missing_findings",
				detail=f"missing={missing_sorted}; extra=[]",
			)
		)
	evidence = sort_evidence(evidence)

	if not missing_sorted:
		return InvariantResult(
			id="finding_integrity",
			status="pass",
			message="All gap/partial requirements have findings.",
			evidence=evidence,
			recommended_action="",
		)

	return InvariantResult(
		id="finding_integrity",
		status="fail",
		message="Gap/partial requirements missing findings.",
		evidence=evidence,
		recommended_action="add_findings",
	)

