from __future__ import annotations

import re
from typing import Dict, List

from app.backend import constants
from app.backend.adapters import sqlite_adapter
from app.backend.validators.matrix_parser import parse_core_rows
from app.backend.validators.playbook_parser import parse_findings
from app.backend.validators.rfc_normative import extract_normative_lines


_BLOCKER_RE = re.compile(r"F-\d{3}")


def _parse_wave1_blockers(handoff_path: str) -> List[str]:
	with open(handoff_path, "r", encoding="utf-8") as handle:
		lines = handle.readlines()

	blockers: List[str] = []
	inside = False
	for line in lines:
		if line.strip().lower().startswith("## wave-1 blockers"):
			inside = True
			continue
		if inside and line.strip().startswith("## "):
			break
		if inside:
			blockers.extend(_BLOCKER_RE.findall(line))

	return sorted(set(blockers))


def get_summary() -> Dict[str, object]:
	rfc_count = len(extract_normative_lines(constants.DEFAULT_RFC_PATH))
	matrix_rows = parse_core_rows(constants.DEFAULT_MATRIX_PATH)
	matrix_count = len(matrix_rows)
	parity_status = "pass" if rfc_count == matrix_count else "fail"
	coverage = {"covered": 0, "partial": 0, "gap": 0}
	for row in matrix_rows:
		if row.status in coverage:
			coverage[row.status] += 1

	blockers = _parse_wave1_blockers(constants.DEFAULT_HANDOFF_PATH)
	states = sqlite_adapter.list_finding_states(db_path=constants.DEFAULT_DB_PATH)
	state_map = {row["finding_id"]: row["status"] for row in states}
	unresolved = [bid for bid in blockers if state_map.get(bid) != "ready_for_validation"]

	findings = parse_findings(constants.DEFAULT_PLAYBOOK_PATH)
	total = len(findings)
	wave1 = sum(1 for f in findings if f.is_wave1_blocker)
	by_wave = {"1": wave1, "2": max(total - wave1, 0)}
	by_severity = {"CRITICAL": wave1}

	return {
		"parity": {
			"rfc_normative_count": rfc_count,
			"matrix_core_count": matrix_count,
			"status": parity_status,
		},
		"coverage": coverage,
		"blockers": {"wave1": blockers, "unresolved": unresolved},
		"findings": {"total": total, "by_wave": by_wave, "by_severity": by_severity},
		"storage": sqlite_adapter.get_storage_meta(constants.DEFAULT_DB_PATH),
	}
