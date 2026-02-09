from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


ReviewVerdict = Literal["approved", "revise", "rejected"]
SafetyVerdict = Literal["pass", "block"]
ReleaseVerdict = Literal["pass", "block"]
ProfileMode = Literal["strict", "compat"]


@dataclass
class UpgradeSpec:
    upgrade_id: str
    goal: str
    allowed_paths: List[str]
    forbidden_paths: List[str]
    required_checks: List[str]
    risk_class: Literal["low", "medium", "high"]
    default_prompt_book_technique: str
    success_predicate: str


@dataclass
class ProposalEdit:
    path: str
    operation: Literal["replace", "write", "append", "prepend"]
    old_text: Optional[str] = None
    new_text: Optional[str] = None


@dataclass
class Dev3Proposal:
    proposal_id: str
    upgrade_id: str
    goal: str
    rationale: str
    edits: List[ProposalEdit]
    expected_effect: str
    risk_notes: List[str] = field(default_factory=list)
    sources: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class Dev4Review:
    verdict: ReviewVerdict
    reasons: List[str] = field(default_factory=list)


@dataclass
class Dev7SafetyVerdict:
    verdict: SafetyVerdict
    reasons: List[str] = field(default_factory=list)


@dataclass
class Dev8ReleaseVerdict:
    verdict: ReleaseVerdict
    reasons: List[str] = field(default_factory=list)


@dataclass
class CycleDiagnostics:
    cycle: int
    profile: ProfileMode
    weakest_dimension: str
    latest_scores: Dict[str, float]
    accepted_upgrades_total: int
    accepted_upgrade_ids: List[str] = field(default_factory=list)
    prior_failures: int = 0


@dataclass
class CycleScores:
    workflow: float
    reliability: float
    ux: float
    safety: float
    release: float
    x_gate_100: float
    x_composite_100: float
    score_delta: float
    gate_smoke_passed: bool
    gate_stress_passed: bool
    gate_checks_pass: bool


@dataclass
class CycleDecision:
    checks_green: bool
    accepted_upgrade_id: Optional[str]
    rollback_triggered: bool
    commit_hash: Optional[str]
    target_reached_reason: str
    should_stop: bool


@dataclass
class CycleRecordV2:
    run_id: str
    profile: ProfileMode
    cycle: int
    prompt_technique: str
    proposal_summary: str
    files_changed: List[str]
    checks_pass: bool
    gate_smoke_passed: bool
    gate_stress_passed: bool
    x_gate_100: float
    x_composite_100: float
    improved: bool
    commit_hash: Optional[str]
    timestamp_utc: str
    dev1_cycle_state: str
    dev3_proposal_id: str
    dev3_sources: List[Dict[str, str]]
    dev4_verdict: ReviewVerdict
    dev4_reasons: List[str]
    dev5_eval_score: Dict[str, float]
    dev6_ux_verdict: str
    dev7_safety_verdict: SafetyVerdict
    dev8_release_verdict: ReleaseVerdict
    accepted_upgrade_id: Optional[str]
    accepted_upgrades_total: int
    score_delta: float
    rollback_triggered: bool
    target_reached_reason: str
    deprecated_flags_used: List[str] = field(default_factory=list)
    cycle_error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "profile": self.profile,
            "cycle": self.cycle,
            "prompt_technique": self.prompt_technique,
            "proposal_summary": self.proposal_summary,
            "files_changed": self.files_changed,
            "checks_pass": self.checks_pass,
            "gate_smoke_passed": self.gate_smoke_passed,
            "gate_stress_passed": self.gate_stress_passed,
            "x_gate_100": self.x_gate_100,
            "x_composite_100": self.x_composite_100,
            "improved": self.improved,
            "commit_hash": self.commit_hash,
            "timestamp_utc": self.timestamp_utc,
            "dev1_cycle_state": self.dev1_cycle_state,
            "dev3_proposal_id": self.dev3_proposal_id,
            "dev3_sources": self.dev3_sources,
            "dev4_verdict": self.dev4_verdict,
            "dev4_reasons": self.dev4_reasons,
            "dev5_eval_score": self.dev5_eval_score,
            "dev6_ux_verdict": self.dev6_ux_verdict,
            "dev7_safety_verdict": self.dev7_safety_verdict,
            "dev8_release_verdict": self.dev8_release_verdict,
            "accepted_upgrade_id": self.accepted_upgrade_id,
            "accepted_upgrades_total": self.accepted_upgrades_total,
            "score_delta": self.score_delta,
            "rollback_triggered": self.rollback_triggered,
            "target_reached_reason": self.target_reached_reason,
            "deprecated_flags_used": self.deprecated_flags_used,
            "cycle_error": self.cycle_error,
        }
