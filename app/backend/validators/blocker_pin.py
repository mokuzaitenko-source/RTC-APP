from __future__ import annotations

import re
from typing import List

from .evidence import sort_evidence
from .playbook_parser import parse_findings
from .types import EvidenceItem, InvariantResult, ValidatorContext


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


def check(ctx: ValidatorContext) -> InvariantResult:
	blockers = _parse_wave1_blockers(ctx.handoff_path)
	playbook = {f.finding_id: f for f in parse_findings(ctx.playbook_path)}
	missing: List[str] = []
	unmarked: List[str] = []
	for finding_id in blockers:
		finding = playbook.get(finding_id)
		if finding is None:
			missing.append(finding_id)
			continue
		if not finding.is_wave1_blocker:
			unmarked.append(finding_id)

	evidence_items: List[EvidenceItem] = []
	if missing or unmarked:
		evidence_items.append(
			EvidenceItem(
				kind="id_list",
				ref="wave1_blockers",
				detail=f"missing={sorted(missing)}; unmarked={sorted(unmarked)}",
			)
		)

	evidence = sort_evidence(evidence_items)
	if not missing and not unmarked:
		return InvariantResult(
			id="blocker_pin",
			status="pass",
			message="Wave-1 blockers are present and marked in playbook.",
			evidence=evidence,
			recommended_action="",
		)

	return InvariantResult(
		id="blocker_pin",
		status="fail",
		message="Wave-1 blockers missing or unmarked in playbook.",
		evidence=evidence,
		recommended_action="restore_blockers",
	)
