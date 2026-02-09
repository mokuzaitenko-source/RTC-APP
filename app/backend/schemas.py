from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ApiError(BaseModel):
	model_config = ConfigDict(extra="forbid")

	code: str
	message: str
	evidence: List[str] = Field(default_factory=list)


class ApiEnvelope(BaseModel):
	model_config = ConfigDict(extra="allow")

	ok: bool
	generated_at: str
	request_id: Optional[str] = None
	run_event: Optional[Dict[str, Any]] = None
	report: Optional[Dict[str, Any]] = None
	data: Optional[Dict[str, Any]] = None
	error: Optional[ApiError] = None


class FindingStateUpdate(BaseModel):
	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

	status: Literal["unstarted", "in_progress", "blocked", "ready_for_validation"] = Field(
		..., description="unstarted | in_progress | blocked | ready_for_validation"
	)
	note: Optional[str] = None


class AssistantRespondRequest(BaseModel):
	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

	user_input: str = Field(..., min_length=1, description="Primary user request.")
	context: Optional[str] = Field(default=None, description="Optional supporting context.")
	risk_tolerance: Literal["low", "medium", "high"] = Field(default="medium")
	max_questions: int = Field(default=2, ge=0, le=2)
	model: Optional[str] = Field(default=None, description="Optional model override from allowlist.")


class AssistantStreamRequest(BaseModel):
	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

	user_input: str = Field(..., min_length=1, description="Primary user request.")
	context: Optional[str] = Field(default=None, description="Optional supporting context.")
	risk_tolerance: Literal["low", "medium", "high"] = Field(default="medium")
	max_questions: int = Field(default=2, ge=0, le=2)
	model: Optional[str] = Field(default=None, description="Optional model override from allowlist.")


class AssistantRespondV2Request(BaseModel):
	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

	user_input: str = Field(..., min_length=1, description="Primary user request.")
	context: Optional[str] = Field(default=None, description="Optional supporting context.")
	risk_tolerance: Literal["low", "medium", "high"] = Field(default="medium")
	max_questions: int = Field(default=2, ge=0, le=2)
	model: Optional[str] = Field(default=None, description="Optional model override from allowlist.")
	trace: bool = Field(default=False, description="Include ACA trace in response payload.")


class AssistantStreamV2Request(BaseModel):
	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

	user_input: str = Field(..., min_length=1, description="Primary user request.")
	context: Optional[str] = Field(default=None, description="Optional supporting context.")
	risk_tolerance: Literal["low", "medium", "high"] = Field(default="medium")
	max_questions: int = Field(default=2, ge=0, le=2)
	model: Optional[str] = Field(default=None, description="Optional model override from allowlist.")
	trace: bool = Field(default=False, description="Emit trace/checkpoint SSE events.")


class AssistantModelsData(BaseModel):
	model_config = ConfigDict(extra="forbid")

	models: List[str] = Field(default_factory=list)
	default_model: str
	provider_mode: Literal["auto", "openai", "local"]
	effective_provider_mode: Literal["openai", "local"]
	provider_ready: bool = True
	provider_warnings: List[str] = Field(default_factory=list)


class ACATraceEvent(BaseModel):
	model_config = ConfigDict(extra="forbid")

	module_id: str
	module_name: str
	tier: Literal["tier0_safety", "tier1_meta", "tier2_bottleneck", "tier3_operational"]
	status: Literal["pass", "adjusted", "fallback", "blocked", "stub"]
	detail: str
	timestamp: str


class AssistantV2ResponseData(BaseModel):
	model_config = ConfigDict(extra="forbid")

	aca_version: Literal["4.1"]
	session_id: str
	mode: Literal["clarify", "plan_execute"]
	final_message: str
	decision_graph: List[Dict[str, Any]] = Field(default_factory=list)
	module_outputs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
	quality: Dict[str, Any] = Field(default_factory=dict)
	safety: Dict[str, Any] = Field(default_factory=dict)
	fallback: Dict[str, Any] = Field(default_factory=dict)
	lane_used: Literal["quick", "governed"] = "governed"
	complexity_reasons: List[str] = Field(default_factory=list)
	pqs_overall: float = 0.0
	fallback_level: int = 0
	assumptions: List[str] = Field(default_factory=list)
	intake_frame: Dict[str, Any] = Field(default_factory=dict)
	adaptive_defaults: Dict[str, Any] = Field(default_factory=dict)
	adaptive_evolution: List[Dict[str, Any]] = Field(default_factory=list)
	runtime_metrics: Dict[str, Any] = Field(default_factory=dict)
	trace: Optional[List[ACATraceEvent]] = None
