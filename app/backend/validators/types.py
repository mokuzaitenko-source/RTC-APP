# app/backend/validators/types.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class EvidenceItem:
	kind: str
	ref: str
	detail: str
	hash: Optional[str] = None


@dataclass(frozen=True)
class InvariantResult:
	id: str
	status: str
	message: str
	evidence: List[EvidenceItem]
	recommended_action: str
	suggested_matches: Optional[List[dict]] = None


@dataclass(frozen=True)
class ValidatorReport:
	run_id: str
	run_type: str
	status: str
	started_at: datetime
	ended_at: datetime
	invariants: List[InvariantResult]
	summary: str


@dataclass(frozen=True)
class NormativeLine:
	rfc_line_id: str
	normative_level: str
	text: str
	hash: str
	line_number: int


@dataclass(frozen=True)
class RequirementRow:
	req_id: str
	status: str
	findings: List[str]
	source_ref: str
	enforcement_tbd: bool = False
	proof_tbd: bool = False


@dataclass(frozen=True)
class FindingInfo:
	finding_id: str
	dependencies: List[str]
	impacted_req_ids: List[str]
	is_wave1_blocker: bool = False


@dataclass(frozen=True)
class RunRecords:
	sync_exit_code: Optional[int] = None
	validate_exit_code: Optional[int] = None


@dataclass
class ValidatorContext:
	rfc_path: str
	matrix_path: str
	playbook_path: str
	handoff_path: str
	run_records: Optional[RunRecords] = None
	workspace_root: Optional[str] = None
	orphan_mapping_mode: str = "source_line"
	state_db_path: Optional[str] = None
