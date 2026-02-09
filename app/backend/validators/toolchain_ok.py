# app/backend/validators/toolchain_ok.py
from __future__ import annotations

from .evidence import sort_evidence
from .types import EvidenceItem, InvariantResult, ValidatorContext


def check(ctx: ValidatorContext) -> InvariantResult:
	if ctx.run_records is None:
		evidence = sort_evidence(
			[EvidenceItem(kind="summary", ref="run_records", detail="missing_run_records=true")]
		)
		return InvariantResult(
			id="toolchain_ok",
			status="fail",
			message="Toolchain checks failed.",
			evidence=evidence,
			recommended_action="run_sync_or_validate",
		)

	sync_code = ctx.run_records.sync_exit_code
	validate_code = ctx.run_records.validate_exit_code
	detail = f"sync_exit_code={sync_code}, validate_exit_code={validate_code}"
	evidence = sort_evidence([EvidenceItem(kind="summary", ref="exit_codes", detail=detail)])
	if sync_code == 0 and validate_code == 0:
		return InvariantResult(
			id="toolchain_ok",
			status="pass",
			message="Toolchain checks passed.",
			evidence=evidence,
			recommended_action="",
		)

	return InvariantResult(
		id="toolchain_ok",
		status="fail",
		message="Toolchain checks failed.",
		evidence=evidence,
		recommended_action="run_sync_or_validate",
	)

