# app/backend/validators/matrix_parser.py
from __future__ import annotations

from typing import List

from .types import RequirementRow


def _split_row(line: str) -> List[str]:
	parts = [part.strip() for part in line.strip().strip("|").split("|")]
	return parts


def _parse_findings(value: str) -> List[str]:
	if not value or value.strip() in {"-", "n/a", "N/A"}:
		return []
	raw = [item.strip() for item in value.split(",")]
	return [item for item in raw if item]


def _is_tbd(value: str) -> bool:
	return "tbd" in value.lower()


def parse_core_rows(matrix_path: str) -> List[RequirementRow]:
	with open(matrix_path, "r", encoding="utf-8") as handle:
		lines = handle.readlines()

	header_idx = None
	for i, line in enumerate(lines):
		if line.strip().startswith("|") and "Req ID" in line:
			header_idx = i
			break
	if header_idx is None:
		return []

	headers = _split_row(lines[header_idx])
	separator_idx = header_idx + 1
	data_start = separator_idx + 1

	rows: List[RequirementRow] = []
	for line in lines[data_start:]:
		if not line.strip().startswith("|"):
			break
		parts = _split_row(line)
		if len(parts) != len(headers):
			continue
		row = dict(zip(headers, parts))
		req_id = row.get("Req ID", "").strip()
		if not req_id:
			continue
		status = row.get("Status", "").strip()
		findings = _parse_findings(row.get("Finding", ""))
		source_ref = row.get("Source", "").strip()
		enforcement_point = row.get("Enforcement Point", "").strip()
		telemetry_proof = row.get("Telemetry Proof", "").strip()
		test = row.get("Test", "").strip()
		enforcement_tbd = _is_tbd(enforcement_point)
		proof_tbd = _is_tbd(telemetry_proof) or _is_tbd(test)
		rows.append(
			RequirementRow(
				req_id=req_id,
				status=status,
				findings=findings,
				source_ref=source_ref,
				enforcement_tbd=enforcement_tbd,
				proof_tbd=proof_tbd,
			)
		)
	return rows

