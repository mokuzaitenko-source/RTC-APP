from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal


RiskTolerance = Literal["low", "medium", "high"]
ProviderMode = Literal["auto", "openai", "local"]
TraceTier = Literal["tier0_safety", "tier1_meta", "tier2_bottleneck", "tier3_operational"]
TraceStatus = Literal["pass", "adjusted", "fallback", "blocked", "stub"]


@dataclass
class ACATraceEvent:
	module_id: str
	module_name: str
	tier: TraceTier
	status: TraceStatus
	detail: str
	timestamp: str

	def as_dict(self) -> Dict[str, str]:
		return {
			"module_id": self.module_id,
			"module_name": self.module_name,
			"tier": self.tier,
			"status": self.status,
			"detail": self.detail,
			"timestamp": self.timestamp,
		}


@dataclass
class ACARequest:
	user_input: str
	context: str | None
	risk_tolerance: RiskTolerance
	max_questions: int
	model: str
	provider_mode: ProviderMode
	session_id: str | None
	trace_enabled: bool = False


@dataclass
class ACAState:
	request: ACARequest
	working_input: str = ""
	working_context: str | None = None
	identity_tag: str = "GENERIC"
	preferences: Dict[str, Any] = field(default_factory=dict)
	meta_policy: Dict[str, Any] = field(default_factory=dict)
	mode_context: Dict[str, Any] = field(default_factory=dict)
	path_context: Dict[str, Any] = field(default_factory=dict)
	mixer_context: Dict[str, Any] = field(default_factory=dict)
	regulation_context: Dict[str, Any] = field(default_factory=dict)
	bottleneck_context: Dict[str, Any] = field(default_factory=dict)
	attention_context: Dict[str, Any] = field(default_factory=dict)
	process_plan: List[str] = field(default_factory=list)
	decision_tree: List[Dict[str, Any]] = field(default_factory=list)
	outline: List[Dict[str, Any]] = field(default_factory=list)
	decision_graph: List[Dict[str, Any]] = field(default_factory=list)
	module_outputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
	prompt_injection_detected: bool = False
	untrusted_tool_instruction_detected: bool = False
	quality_score: float = 0.0
	safety: Dict[str, Any] = field(default_factory=dict)
	fallback: Dict[str, Any] = field(default_factory=dict)
	result: Dict[str, object] = field(default_factory=dict)
	trace: List[ACATraceEvent] = field(default_factory=list)
