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


class AssistantModelsData(BaseModel):
	model_config = ConfigDict(extra="forbid")

	models: List[str] = Field(default_factory=list)
	default_model: str
	provider_mode: Literal["auto", "openai", "local"]
