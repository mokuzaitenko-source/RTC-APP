# app/backend/validators/playbook_parser.py
from __future__ import annotations

import re
from typing import Dict, List, Optional

from .types import FindingInfo


_FINDING_RE = re.compile(r"^###\s+(F-\d{3})")
_WAVE1_RE = re.compile(r"^##\s+Wave\s+1", re.IGNORECASE)
_SECTION_RE = re.compile(r"^##\s+")
_IMPACT_HEADER_RE = re.compile(r"^\**\s*impacted requirement ids\s*:?\s*\**$", re.IGNORECASE)
_DEP_HEADER_RE = re.compile(r"^\**\s*dependencies\s*:?\s*\**$", re.IGNORECASE)
_IMP_REQ_RE = re.compile(r"^\-\s+`((?:REQ|R)-[A-Za-z0-9.\-]+)`", re.IGNORECASE)
_DEP_RE = re.compile(r"^\-\s+`(F-\d{3})`")


def parse_findings(playbook_path: str) -> List[FindingInfo]:
	findings: Dict[str, FindingInfo] = {}
	current_id: Optional[str] = None
	in_wave1 = False
	parsing_impacts = False
	parsing_deps = False
	with open(playbook_path, "r", encoding="utf-8") as handle:
		for raw in handle:
			line = raw.strip()
			if _WAVE1_RE.match(line):
				in_wave1 = True
				continue
			if _SECTION_RE.match(line) and not _WAVE1_RE.match(line):
				in_wave1 = False
			match = _FINDING_RE.match(line)
			if match:
				current_id = match.group(1)
				findings[current_id] = FindingInfo(
					finding_id=current_id,
					dependencies=[],
					impacted_req_ids=[],
					is_wave1_blocker=in_wave1,
				)
				parsing_impacts = False
				parsing_deps = False
				continue
			if current_id is None:
				continue
			if _IMPACT_HEADER_RE.match(line):
				parsing_impacts = True
				parsing_deps = False
				continue
			if _DEP_HEADER_RE.match(line):
				parsing_deps = True
				parsing_impacts = False
				continue
			if line.startswith("---") or line.startswith("### "):
				parsing_impacts = False
				parsing_deps = False
				continue
			if parsing_impacts:
				impact_match = _IMP_REQ_RE.match(line)
				if impact_match:
					findings[current_id].impacted_req_ids.append(impact_match.group(1).upper())
				continue
			if parsing_deps:
				dep_match = _DEP_RE.match(line)
				if dep_match:
					findings[current_id].dependencies.append(dep_match.group(1))
				continue

	return list(findings.values())
