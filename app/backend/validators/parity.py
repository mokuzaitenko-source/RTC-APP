# app/backend/validators/parity.py
from __future__ import annotations

from .evidence import build_file_line_ref, sort_evidence
from .rfc_normative import extract_normative_lines
from .matrix_parser import parse_core_rows
from .types import EvidenceItem, InvariantResult, ValidatorContext


def check(ctx: ValidatorContext) -> InvariantResult:
	rfc_lines = extract_normative_lines(ctx.rfc_path)
	rows = parse_core_rows(ctx.matrix_path)
	rfc_count = len(rfc_lines)
	matrix_count = len(rows)
	evidence_items = []
	if rfc_lines:
		first = rfc_lines[0]
		evidence_items.append(
			EvidenceItem(
				kind="file_line",
				ref=build_file_line_ref(
					ctx.rfc_path,
					first.line_number,
					workspace_root=ctx.workspace_root,
				),
				detail=first.text,
				hash=first.hash,
			)
		)
	evidence_items.append(
		EvidenceItem(
			kind="summary",
			ref="counts",
			detail=f"rfc={rfc_count}, matrix={matrix_count}",
		)
	)
	evidence = sort_evidence(evidence_items)

	if rfc_count == matrix_count:
		return InvariantResult(
			id="parity",
			status="pass",
			message="RFC normative line count matches matrix core rows.",
			evidence=evidence,
			recommended_action="",
		)

	return InvariantResult(
		id="parity",
		status="fail",
		message="RFC normative line count does not match matrix core rows.",
		evidence=evidence,
		recommended_action="repair_parity",
	)

