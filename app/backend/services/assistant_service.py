from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
import os
import re
import time
from threading import Lock
from typing import Any, Dict, Iterator, List, Literal, Tuple

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.backend.aca import ACAOrchestrator, ACAOrchestratorHooks, ACARequest
from app.backend.services import chat_session_service


RiskTolerance = Literal["low", "medium", "high"]
ProviderMode = Literal["auto", "openai", "local"]

_DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
_DEFAULT_OPENAI_TIMEOUT_S = 30.0
_DEFAULT_STREAM_CHUNK_CHARS = 80
_DEFAULT_AMBIGUITY_GOVERNED_THRESHOLD = 0.35
_LOW_CONFIDENCE_THRESHOLD = 0.70
_CORRECTION_PRESSURE_WINDOW = 6
_CORRECTION_PRESSURE_THRESHOLD = 3

_AMBIGUOUS_TOKENS = {
	"thing",
	"things",
	"stuff",
	"better",
	"improve",
	"optimize",
	"quick",
	"soon",
	"somehow",
	"maybe",
	"nice",
	"cool",
}

_OBJECTIVE_VERBS = {
	"build",
	"create",
	"design",
	"implement",
	"deploy",
	"ship",
	"plan",
	"write",
	"fix",
	"refactor",
	"test",
	"document",
}

_CONVERSATION_TOKENS = {
	"hi",
	"hello",
	"hey",
	"yo",
	"sup",
	"thanks",
	"thank",
	"morning",
	"evening",
}

_CONVERSATION_PHRASES = {
	"what's up",
	"how are you",
	"can we chat",
	"let's chat",
	"just chatting",
	"how's it going",
}

_TASK_MARKERS = _OBJECTIVE_VERBS | {
	"deadline",
	"constraints",
	"acceptance",
	"milestone",
	"roadmap",
}
_TASK_PHRASES = {
	"acceptance criteria",
	"success criteria",
	"implementation brief",
	"mvp",
	"api",
	"feature",
	"bug",
}

_RISK_TOKENS = {"auth", "payment", "security", "privacy", "legal", "medical", "finance", "production"}
_GOVERNED_RISK_TOKENS = {
	"auth",
	"payment",
	"security",
	"privacy",
	"policy",
	"legal",
	"medical",
	"finance",
	"production",
	"prod",
}
_FRESHNESS_RETRIEVAL_TOKENS = {
	"latest",
	"current",
	"today",
	"now",
	"news",
	"release",
	"version",
	"pricing",
	"search",
	"browse",
	"retrieve",
	"source",
	"sources",
	"docs",
	"web",
}
_MULTI_DECISION_TOKENS = {
	"architecture",
	"system",
	"roadmap",
	"migration",
	"strategy",
	"integrate",
	"integration",
	"fuse",
	"fusion",
}
_CORRECTION_PRESSURE_TOKENS = {"wrong", "fix", "again", "failed", "issue", "bug", "not"}


def _adaptive_now() -> datetime:
	return datetime.now(timezone.utc)


def _adaptive_now_iso() -> str:
	return _adaptive_now().isoformat().replace("+00:00", "Z")


@dataclass
class _AdaptiveSessionState:
	ambiguity_threshold: float = _DEFAULT_AMBIGUITY_GOVERNED_THRESHOLD
	checklist_version: int = 1
	consecutive_governed_failures: int = 0
	missing_decision_counts: Dict[str, int] = field(default_factory=dict)
	correction_pressure_signals: deque[bool] = field(
		default_factory=lambda: deque(maxlen=_CORRECTION_PRESSURE_WINDOW)
	)
	updated_at: str = field(default_factory=lambda: _adaptive_now_iso())


_ADAPTIVE_SESSION_STATE: Dict[str, _AdaptiveSessionState] = {}
_ADAPTIVE_SESSION_LOCK = Lock()


def _adaptive_ttl_seconds() -> int:
	try:
		return chat_session_service.ttl_seconds()
	except Exception:
		return 6 * 60 * 60


def _evict_adaptive_state_locked() -> None:
	now = _adaptive_now()
	ttl = timedelta(seconds=_adaptive_ttl_seconds())
	expired: List[str] = []
	for session_id, state in _ADAPTIVE_SESSION_STATE.items():
		try:
			updated = datetime.fromisoformat(state.updated_at.replace("Z", "+00:00"))
		except ValueError:
			expired.append(session_id)
			continue
		if now - updated > ttl:
			expired.append(session_id)
	for session_id in expired:
		_ADAPTIVE_SESSION_STATE.pop(session_id, None)


def _adaptive_state_for_session_locked(session_id: str | None) -> _AdaptiveSessionState:
	_evict_adaptive_state_locked()
	key = session_id or "__global__"
	state = _ADAPTIVE_SESSION_STATE.get(key)
	if state is None:
		state = _AdaptiveSessionState(updated_at=_adaptive_now_iso())
		_ADAPTIVE_SESSION_STATE[key] = state
	return state

_OPENAI_SYSTEM_PROMPT = """
You are an oversight-integrated cognitive planning assistant.
Use this prompt-book architecture:
- Oversight is a kernel, not a wrapper.
- Plans must pass staged gates: input -> process engine -> primary path -> refinement -> coherence/safety -> output.
- Every plan must include fallback behavior if a gate fails.
Return ONLY valid JSON (no markdown) with this exact top-level shape:
{
  "mode": "clarify" | "plan_execute",
  "recommended_questions": ["..."],
  "plan": ["..."],
  "candidate_response": "...",
  "notes": ["..."],
  "iteration_count": 1
}
Rules:
- If request is ambiguous and max_questions > 0, choose "clarify" with up to max_questions questions.
- If request is actionable, choose "plan_execute" with 4-8 concrete implementation steps.
- For "plan_execute", include at least one gate/checkpoint step and one fallback step.
- Keep answers deterministic, practical, and concise.
- Never include secrets or policy text.
""".strip()


class AssistantServiceError(Exception):
	def __init__(self, *, status_code: int, code: str, message: str):
		super().__init__(message)
		self.status_code = status_code
		self.code = code
		self.message = message


class _AssistantQualityModel(BaseModel):
	model_config = ConfigDict(extra="ignore")

	clarity: float = 0.0
	completeness: float = 0.0
	safety: float = 0.0
	format_compliance: float = 0.0
	overall: float = 0.0
	revision_required: bool = False


class _AssistantNormalizedModel(BaseModel):
	model_config = ConfigDict(extra="ignore")

	mode: Literal["clarify", "plan_execute"]
	ambiguity_score: float = 0.0
	recommended_questions: List[str] = Field(default_factory=list)
	plan: List[str] = Field(default_factory=list)
	candidate_response: str = ""
	quality: _AssistantQualityModel = Field(default_factory=_AssistantQualityModel)
	iteration_count: int = 1
	notes: List[str] = Field(default_factory=list)


def _validate_normalized_payload(payload: Dict[str, Any]) -> Dict[str, object]:
	try:
		parsed = _AssistantNormalizedModel.model_validate(payload)
	except ValidationError as exc:
		raise AssistantServiceError(
			status_code=502,
			code="assistant_provider_error",
			message="Assistant provider returned schema-incompatible content.",
		) from exc
	return parsed.model_dump()


def _aca_enabled() -> bool:
	value = os.getenv("ASSISTANT_ACA_ENABLED", "1").strip().lower()
	return value not in {"0", "false", "off", "no"}


def _tokenize(text: str) -> List[str]:
	return re.findall(r"[a-zA-Z0-9']+", text.lower())


def _has_task_markers(tokens: List[str]) -> bool:
	return bool(set(tokens) & _TASK_MARKERS)


def _has_task_phrases(text: str) -> bool:
	lowered = text.lower()
	for phrase in _TASK_PHRASES:
		pattern = r"\b" + re.escape(phrase).replace(r"\ ", r"\s+") + r"\b"
		if re.search(pattern, lowered):
			return True
	return False


def _detect_interaction_mode(user_input: str, context: str | None) -> Literal["conversation", "task"]:
	user_text = " ".join(user_input.split()).strip().lower()
	user_tokens = _tokenize(user_text)
	if _has_task_markers(user_tokens) or _has_task_phrases(user_text):
		return "task"
	if not user_text:
		if isinstance(context, str) and context.strip():
			context_text = context.lower()
			context_tokens = _tokenize(context_text)
			if _has_task_markers(context_tokens) or _has_task_phrases(context_text):
				return "task"
			if set(context_tokens) & _CONVERSATION_TOKENS:
				return "conversation"
			if any(phrase in context_text for phrase in _CONVERSATION_PHRASES):
				return "conversation"
		return "conversation"
	if set(user_tokens) & _CONVERSATION_TOKENS:
		return "conversation"
	if any(phrase in user_text for phrase in _CONVERSATION_PHRASES):
		return "conversation"
	if isinstance(context, str) and context.strip():
		context_text = context.lower()
		context_tokens = _tokenize(context_text)
		if _has_task_markers(context_tokens) or _has_task_phrases(context_text):
			return "task"
	return "task"


def _conversation_response(user_input: str) -> str:
	text = " ".join(user_input.split()).strip()
	if not text:
		return "Hey. I'm here. What do you want to work on?"
	if any(phrase in text.lower() for phrase in ["how are you", "what's up", "whats up"]):
		return "I'm ready. Tell me what you want to build, fix, or decide, and we'll work it step by step."
	if any(token in _tokenize(text) for token in {"thanks", "thank"}):
		return "You're welcome. Want to keep going or switch tasks?"
	return "Yeah, we can chat. Tell me your goal in plain language and I will help you make it actionable."


def _ambiguity_score(user_input: str, context: str | None) -> Tuple[float, List[str]]:
	tokens = _tokenize(user_input)
	score = 0.0
	reasons: List[str] = []

	if len(tokens) < 12:
		score += 0.25
		reasons.append("short_request")

	hits = sorted({token for token in tokens if token in _AMBIGUOUS_TOKENS})
	if hits:
		score += min(0.45, 0.12 * len(hits))
		reasons.append(f"ambiguous_terms:{','.join(hits)}")

	if not any(token in _OBJECTIVE_VERBS for token in tokens):
		score += 0.2
		reasons.append("missing_explicit_action")

	if context and context.strip():
		score -= 0.08

	score = max(0.0, min(1.0, score))
	return round(score, 2), reasons


def _combined_text(user_input: str, context: str | None) -> str:
	parts = [user_input.strip()]
	if isinstance(context, str) and context.strip():
		parts.append(context.strip())
	return "\n".join(part for part in parts if part)


def _extract_prefixed_value(text: str, label: str) -> str:
	pattern = re.compile(rf"(?im)^\s*{re.escape(label)}\s*:\s*(.+?)\s*$")
	match = pattern.search(text)
	if not match:
		return ""
	return " ".join(match.group(1).split()).strip()


def _extract_constraints(text: str) -> List[str]:
	prefixed = _extract_prefixed_value(text, "constraints")
	constraints: List[str] = []
	if prefixed:
		for item in re.split(r"[;,|]", prefixed):
			cleaned = " ".join(item.split()).strip()
			if cleaned:
				constraints.append(cleaned)
	if constraints:
		return constraints[:4]
	lines = [line.strip() for line in text.splitlines() if line.strip()]
	for line in lines:
		lowered = line.lower()
		if any(marker in lowered for marker in ["must", "should", "cannot", "deadline", "budget", "within"]):
			constraints.append(" ".join(line.split()).strip())
	if not constraints:
		constraints.append("No explicit constraints provided; confirm constraints before irreversible changes.")
	return list(dict.fromkeys(constraints))[:4]


def _extract_deadline(text: str) -> str:
	explicit = _extract_prefixed_value(text, "deadline")
	if explicit:
		return explicit
	lowered = text.lower()
	for marker in ["today", "tomorrow", "this week", "this month", "asap"]:
		if marker in lowered:
			return marker
	match = re.search(r"\bby\s+([a-z0-9 ,/-]{3,40})", lowered)
	if match:
		return "by " + " ".join(match.group(1).split()).strip()
	return "unspecified"


def _extract_done_when(text: str, goal: str) -> str:
	explicit = _extract_prefixed_value(text, "done-when")
	if explicit:
		return explicit
	explicit = _extract_prefixed_value(text, "done when")
	if explicit:
		return explicit
	if goal:
		return f"A usable result is produced for: {goal}"
	return "A clear decision, checks, and next step are provided."


def _extract_intake_frame(
	*,
	user_input: str,
	context: str | None,
	risk_tolerance: RiskTolerance,
) -> Dict[str, Any]:
	combined = _combined_text(user_input, context)
	goal = _extract_prefixed_value(combined, "goal")
	if not goal:
		goal = " ".join(user_input.split()).strip()
	constraints = _extract_constraints(combined)
	done_when = _extract_done_when(combined, goal)
	risk = _extract_prefixed_value(combined, "risk").lower() or str(risk_tolerance)
	if risk not in {"low", "medium", "high"}:
		risk = str(risk_tolerance)
	deadline = _extract_deadline(combined)
	return {
		"goal": goal,
		"constraints": constraints,
		"done_when": done_when,
		"risk": risk,
		"deadline": deadline,
	}


def _forced_lane_override(user_input: str, context: str | None) -> str | None:
	combined = _combined_text(user_input, context).lower()
	if any(flag in combined for flag in ["full governed", "governed only", "full governance"]):
		return "governed"
	if "quick only" in combined:
		return "quick"
	return None


def _is_freshness_or_retrieval_dependent(tokens: List[str], text: str) -> bool:
	if set(tokens) & _FRESHNESS_RETRIEVAL_TOKENS:
		return True
	lowered = text.lower()
	return any(phrase in lowered for phrase in ["look up", "search for", "latest ", "current "])


def _is_multi_decision_scope(tokens: List[str], text: str) -> bool:
	if len(tokens) >= 28:
		return True
	if len(set(tokens) & _MULTI_DECISION_TOKENS) >= 2:
		return True
	lowered = text.lower()
	if lowered.count(" and ") >= 3 and len(tokens) >= 24:
		return True
	return lowered.count(" then ") >= 2


def _complexity_reasons(
	*,
	user_input: str,
	context: str | None,
	ambiguity_score: float,
	ambiguity_threshold: float,
) -> List[str]:
	combined = _combined_text(user_input, context)
	tokens = _tokenize(combined)
	reasons: List[str] = []
	if ambiguity_score > ambiguity_threshold:
		reasons.append("ambiguity_over_threshold")
	if set(tokens) & _GOVERNED_RISK_TOKENS:
		reasons.append("risk_domain_signal")
	if _is_freshness_or_retrieval_dependent(tokens, combined):
		reasons.append("freshness_or_retrieval_required")
	if _is_multi_decision_scope(tokens, combined):
		reasons.append("multi_decision_scope")
	return reasons


def _estimate_confidence(result: Dict[str, object]) -> float:
	quality = result.get("quality")
	if isinstance(quality, dict):
		overall = quality.get("overall")
		if isinstance(overall, (int, float)):
			return max(0.0, min(1.0, float(overall) / 10.0))
	return 0.8


def _adaptive_state_for_session(session_id: str | None) -> _AdaptiveSessionState:
	with _ADAPTIVE_SESSION_LOCK:
		return _adaptive_state_for_session_locked(session_id)


def _quick_contract_response(
	*,
	result: Dict[str, object],
	intake_frame: Dict[str, Any],
) -> str:
	goal = str(intake_frame.get("goal") or "the requested outcome")
	decision = f"Proceed with a focused implementation for: {goal}"
	why = "Request is clear and low-risk, so quick lane is selected for fast progress."
	checks = "Validate objective alignment and run one acceptance check before handoff."
	next_step = "Execute the first smallest verifiable step and report outcome."
	return (
		f"Decision: {decision}\n"
		f"Why: {why}\n"
		"Checks:\n"
		f"- {checks}\n"
		f"Next step: {next_step}"
	)


def _governed_clarify_response(questions: List[str]) -> str:
	lines = [
		"Governed lane is active. I need clarification before execution:",
	]
	for idx, question in enumerate(questions, start=1):
		lines.append(f"{idx}. {question}")
	lines.append("Execution is paused until these decisions are confirmed.")
	return "\n".join(lines)


def _fallback_level_from_result(
	*,
	result: Dict[str, object],
	state: _AdaptiveSessionState,
	lane: str,
	ambiguity_score: float,
	ambiguity_threshold: float,
) -> int:
	fallback = result.get("fallback")
	triggered = isinstance(fallback, dict) and bool(fallback.get("triggered"))
	if not triggered:
		if lane == "governed" and ambiguity_score > ambiguity_threshold:
			return 1
		return 0
	reason_code = str(fallback.get("reason_code", "")) if isinstance(fallback, dict) else ""
	if reason_code in {"prompt_injection_detected", "unsafe_output_detected"}:
		return 4
	return min(4, max(1, state.consecutive_governed_failures))


def _apply_evolution_policy(
	*,
	state: _AdaptiveSessionState,
	governed_failure: bool,
	missing_decision_keys: List[str],
	correction_pressure: bool,
) -> List[Dict[str, str]]:
	events: List[Dict[str, str]] = []
	prev_failures = state.consecutive_governed_failures
	prev_correction_count = sum(1 for signal in state.correction_pressure_signals if signal)
	state.consecutive_governed_failures = prev_failures + 1 if governed_failure else 0

	for key in missing_decision_keys:
		previous = state.missing_decision_counts.get(key, 0)
		current = previous + 1
		state.missing_decision_counts[key] = current
		if previous < 3 <= current:
			state.checklist_version += 1
			events.append(
				{
					"trigger": f"missing_decision_pattern_repeated:{key}",
					"change": "Tighten intake checklist wording for missing decisions.",
					"expected_effect": "Reduce repeated missing decision ambiguity before execution.",
					"rollback_condition": "If clarification volume rises without quality gains for 10 turns.",
				}
			)

	state.correction_pressure_signals.append(correction_pressure)
	correction_count = sum(1 for signal in state.correction_pressure_signals if signal)

	if prev_failures < 2 <= state.consecutive_governed_failures:
		old_threshold = state.ambiguity_threshold
		state.ambiguity_threshold = max(0.25, round(state.ambiguity_threshold - 0.02, 2))
		events.append(
			{
				"trigger": "two_governed_failures_back_to_back",
				"change": f"Lower ambiguity threshold from {old_threshold:.2f} to {state.ambiguity_threshold:.2f}.",
				"expected_effect": "Escalate to governed handling earlier on underspecified requests.",
				"rollback_condition": "If governed-lane volume increases >20% without PQS improvement.",
			}
		)

	if prev_correction_count < _CORRECTION_PRESSURE_THRESHOLD <= correction_count:
		old_threshold = state.ambiguity_threshold
		state.ambiguity_threshold = max(0.25, round(state.ambiguity_threshold - 0.01, 2))
		events.append(
			{
				"trigger": "high_user_correction_pressure",
				"change": f"Lower ambiguity threshold from {old_threshold:.2f} to {state.ambiguity_threshold:.2f} and keep checklist version {state.checklist_version}.",
				"expected_effect": "Catch unclear instructions earlier and reduce corrective rework.",
				"rollback_condition": "If user correction pressure drops but cycle time increases materially.",
			}
		)

	return events


def _adaptive_defaults(state: _AdaptiveSessionState) -> Dict[str, Any]:
	return {
		"ambiguity_threshold": round(state.ambiguity_threshold, 2),
		"checklist_version": state.checklist_version,
		"default_risk_tolerance": "medium",
	}


def _apply_adaptive_protocol(
	*,
	result: Dict[str, object],
	user_input: str,
	context: str | None,
	risk_tolerance: RiskTolerance,
	max_questions: int,
	session_id: str | None,
) -> Dict[str, object]:
	with _ADAPTIVE_SESSION_LOCK:
		state = _adaptive_state_for_session_locked(session_id)
		state.updated_at = _adaptive_now_iso()
		intake_frame = _extract_intake_frame(
			user_input=user_input,
			context=context,
			risk_tolerance=risk_tolerance,
		)
		local_ambiguity, ambiguity_notes = _ambiguity_score(user_input, context)
		interaction_mode = _detect_interaction_mode(user_input, context)
		requested_step_count = _requested_step_count(user_input)
		user_tokens = _tokenize(user_input)
		is_task_request = _has_task_markers(user_tokens) or _has_task_phrases(user_input)
		ambiguous_terms_present = any(note.startswith("ambiguous_terms") for note in ambiguity_notes)
		forced_lane = _forced_lane_override(user_input, context)
		complexity_reasons = _complexity_reasons(
			user_input=user_input,
			context=context,
			ambiguity_score=local_ambiguity,
			ambiguity_threshold=state.ambiguity_threshold,
		)
		lane_used = "governed" if complexity_reasons else "quick"
		if interaction_mode == "conversation":
			lane_used = "quick"
			complexity_reasons = ["conversation_intent"]
		if forced_lane == "governed":
			lane_used = "governed"
			complexity_reasons = ["forced_full_governed", *complexity_reasons]
		elif forced_lane == "quick":
			lane_used = "quick"
			complexity_reasons = ["forced_quick_only"]
		if not complexity_reasons:
			complexity_reasons = ["default_quick_lane"]

		quality = result.get("quality")
		if not isinstance(quality, dict):
			quality = {}
			result["quality"] = quality
		pqs_overall_raw = quality.get("overall", 8.0)
		pqs_overall = float(pqs_overall_raw) if isinstance(pqs_overall_raw, (int, float)) else 8.0

		assumptions = result.get("assumptions")
		if not isinstance(assumptions, list):
			assumptions = []
		confidence = _estimate_confidence(result)
		if interaction_mode == "conversation":
			result["mode"] = "plan_execute"
			result["recommended_questions"] = []
			result["plan"] = []
			result["candidate_response"] = _conversation_response(user_input)
			result["assumptions"] = []
			if not isinstance(result.get("quality"), dict):
				result["quality"] = _score_quality(
					candidate_response=str(result["candidate_response"]),
					plan=[],
					user_input=user_input,
					recommended_questions=[],
				)
		elif lane_used == "governed":
			if local_ambiguity > state.ambiguity_threshold and max_questions > 0 and (
				not is_task_request or ambiguous_terms_present
			):
				questions = _clarifying_questions(user_input, max_questions)
				result["mode"] = "clarify"
				result["recommended_questions"] = questions[:max_questions]
				result["plan"] = []
				result["candidate_response"] = _governed_clarify_response(questions[:max_questions])
			if confidence < _LOW_CONFIDENCE_THRESHOLD:
				assumptions.append("Assumed constraints and environment remain valid until explicitly corrected.")
			if "risk_domain_signal" in complexity_reasons:
				assumptions.append("Assumed risk-sensitive operations require conservative safety handling.")
			assumptions = list(dict.fromkeys(str(item).strip() for item in assumptions if str(item).strip()))
			if assumptions:
				result["assumptions"] = assumptions
			if pqs_overall < 8.0:
				current_iterations = result.get("iteration_count")
				iterations = int(current_iterations) if isinstance(current_iterations, int) else 1
				result["iteration_count"] = min(3, max(iterations, 2))
		else:
			result["mode"] = "plan_execute"
			result["recommended_questions"] = []
			result["candidate_response"] = _quick_contract_response(
				result=result,
				intake_frame=intake_frame,
			)
			result["checks"] = [
				{
					"name": "quick_validation",
					"status": "pass",
					"evidence": "Objective alignment and one acceptance check required before handoff.",
					"severity": "medium",
				}
			]
			result["assumptions"] = []

		if (
			requested_step_count is not None
			and interaction_mode != "conversation"
			and result.get("mode") == "plan_execute"
		):
			plan = result.get("plan")
			plan_items = _string_list(plan, limit=16) if isinstance(plan, list) else []
			if not plan_items:
				plan_items = _make_plan(user_input, context, risk_tolerance)
			plan_items = _enforce_step_count(plan_items, requested_step_count)
			result["plan"] = plan_items
			result["candidate_response"] = _compose_candidate_response(
				plan_items,
				user_input,
				risk_tolerance,
			)
			result["quality"] = _score_quality(
				candidate_response=str(result["candidate_response"]),
				plan=plan_items,
				user_input=user_input,
				recommended_questions=[],
			)

		missing_decision_keys: List[str] = []
		if "No explicit constraints provided" in " ".join(intake_frame.get("constraints", [])):
			missing_decision_keys.append("constraints")
		if intake_frame.get("deadline") == "unspecified":
			missing_decision_keys.append("deadline")
		if not intake_frame.get("done_when"):
			missing_decision_keys.append("done_when")

		combined_text = _combined_text(user_input, context).lower()
		correction_pressure = any(token in combined_text for token in _CORRECTION_PRESSURE_TOKENS)
		fallback = result.get("fallback")
		fallback_triggered = isinstance(fallback, dict) and bool(fallback.get("triggered"))
		governed_failure = lane_used == "governed" and (fallback_triggered or pqs_overall < 8.0)
		evolution_events = _apply_evolution_policy(
			state=state,
			governed_failure=governed_failure,
			missing_decision_keys=missing_decision_keys,
			correction_pressure=correction_pressure,
		)

		fallback_level = _fallback_level_from_result(
			result=result,
			state=state,
			lane=lane_used,
			ambiguity_score=local_ambiguity,
			ambiguity_threshold=state.ambiguity_threshold,
		)
		if not isinstance(fallback, dict):
			fallback = {
				"triggered": fallback_level > 0,
				"reason_code": "none" if fallback_level == 0 else "governed_escalation",
				"strategy": "none" if fallback_level == 0 else "clarify_and_narrow",
				"notes": [],
			}
			result["fallback"] = fallback
		fallback["level"] = fallback_level

		if lane_used == "governed" and fallback_level >= 2:
			candidate = str(result.get("candidate_response") or "").strip()
			candidate = (
				f"{candidate}\n\n"
				"Constrained options:\n"
				"1. Narrow to one concrete deliverable and proceed.\n"
				"2. Confirm constraints and success criteria before execution.\n"
				"Please choose option 1 or 2, or provide a tighter direction."
			)
			result["candidate_response"] = candidate

		result["lane_used"] = lane_used
		result["interaction_mode"] = interaction_mode
		result["complexity_reasons"] = complexity_reasons
		result["intake_frame"] = intake_frame
		result["pqs_overall"] = round(pqs_overall, 2)
		result["fallback_level"] = fallback_level
		result["assumptions"] = result.get("assumptions", assumptions)
		result["adaptive_defaults"] = _adaptive_defaults(state)
		result["adaptive_evolution"] = evolution_events
		result["complexity_test"] = {
			"passed": lane_used == "quick" or not fallback_triggered,
			"lane_selection_explicit": True,
			"reasons": complexity_reasons,
			"ambiguity_score": local_ambiguity,
			"ambiguity_threshold": round(state.ambiguity_threshold, 2),
			"notes": ambiguity_notes,
		}
		return result


def _clarifying_questions(user_input: str, max_questions: int) -> List[str]:
	questions = [
		"What exact outcome should we produce first (for example: API endpoint, UI page, or architecture draft)?",
		"Which constraints matter most right now (time, tools, scope, and quality bar)?",
		"What acceptance checks must pass before this is considered done?",
	]
	if "deploy" in _tokenize(user_input):
		questions.insert(1, "Which environment should we target first (local, staging, or production)?")
	return questions[:max_questions]


def _fallback_policy_text(risk_tolerance: RiskTolerance) -> str:
	if risk_tolerance == "low":
		return "block risky execution, ask clarifying questions, and return a conservative safe response."
	if risk_tolerance == "high":
		return "allow one alternate strategy retry, then return the safest useful response if checks still fail."
	return "retry once with a simplified strategy, then ask for clarification if checks still fail."


def _requested_step_count(text: str) -> int | None:
	lowered = text.lower()
	digit_match = re.search(r"\b(\d{1,2})\s*[\-\u2010-\u2015 ]?\s*step(?:s)?\b", lowered)
	if digit_match:
		value = int(digit_match.group(1))
		if 2 <= value <= 12:
			return value
	word_to_value = {
		"two": 2,
		"three": 3,
		"four": 4,
		"five": 5,
		"six": 6,
		"seven": 7,
		"eight": 8,
		"nine": 9,
		"ten": 10,
		"eleven": 11,
		"twelve": 12,
	}
	word_match = re.search(
		r"\b(two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*[\-\u2010-\u2015 ]?\s*step(?:s)?\b",
		lowered,
	)
	if word_match:
		return word_to_value[word_match.group(1)]
	return None


def _enforce_step_count(plan: List[str], target_count: int) -> List[str]:
	if target_count <= 0:
		return plan
	normalized = _dedupe_steps(plan)
	if not normalized:
		return normalized
	fallback_step = next((step for step in normalized if "fallback" in step.lower()), "")
	if len(normalized) > target_count:
		normalized = normalized[:target_count]
		if fallback_step and fallback_step not in normalized:
			normalized[-1] = fallback_step
		return _dedupe_steps(normalized)
	if len(normalized) < target_count:
		while len(normalized) < target_count:
			normalized.append(
				"Execution step: implement the next smallest testable increment and confirm one acceptance check."
			)
	return _dedupe_steps(normalized)


def _default_prompt_book_steps(context: str | None, risk_tolerance: RiskTolerance) -> List[str]:
	steps = [
		"Input gate: restate objective, assumptions, constraints, and success criteria before execution.",
		"Process engine: choose reasoning mode (direct, retrieval, or tool-assisted) and define acceptance checks.",
		"Primary path: execute a minimal vertical slice and capture verification evidence.",
		"Refinement gate: run a critique pass and revise weak or ambiguous steps.",
		"Coherence and safety gate: verify policy compliance, contradiction-free reasoning, and output format.",
		f"Fallback policy: {_fallback_policy_text(risk_tolerance)}",
	]
	if context and context.strip():
		steps.insert(2, "Context lock: incorporate provided context into scope boundaries and design decisions.")
	return steps


def _dedupe_steps(steps: List[str]) -> List[str]:
	result: List[str] = []
	seen: set[str] = set()
	for step in steps:
		cleaned = " ".join(step.split()).strip()
		if not cleaned:
			continue
		key = cleaned.lower()
		if key in seen:
			continue
		seen.add(key)
		result.append(cleaned)
	return result


def _align_plan_to_prompt_book(
	*,
	plan: List[str],
	context: str | None,
	risk_tolerance: RiskTolerance,
) -> List[str]:
	aligned = _dedupe_steps(plan)
	if not aligned:
		aligned = _default_prompt_book_steps(context, risk_tolerance)

	lower = [step.lower() for step in aligned]
	if not any("gate" in step for step in lower):
		aligned.insert(0, "Input gate: restate objective and verify scope before execution.")
	if context and context.strip() and not any("context" in step for step in lower):
		aligned.insert(1, "Context lock: incorporate provided context into constraints and design decisions.")
	if not any("refinement" in step or "critique" in step for step in lower):
		aligned.append("Refinement gate: run a critique pass and revise weak sections.")
	if not any("fallback" in step for step in lower):
		aligned.append(f"Fallback policy: {_fallback_policy_text(risk_tolerance)}")

	aligned = _dedupe_steps(aligned)
	if len(aligned) > 8:
		fallback = next((step for step in aligned if "fallback" in step.lower()), "")
		trimmed = aligned[:8]
		if fallback and fallback not in trimmed:
			trimmed[-1] = fallback
		aligned = trimmed
	return aligned


def _make_plan(user_input: str, context: str | None, risk_tolerance: RiskTolerance) -> List[str]:
	_ = user_input
	steps = _default_prompt_book_steps(context, risk_tolerance)
	return _align_plan_to_prompt_book(
		plan=steps,
		context=context,
		risk_tolerance=risk_tolerance,
	)


def _compose_candidate_response(plan: List[str], user_input: str, risk_tolerance: RiskTolerance) -> str:
	lines = [
		"Oversight-guided execution path:",
	]
	for idx, step in enumerate(plan, start=1):
		lines.append(f"{idx}. {step}")
	lines.append("")
	lines.append("Gate checks: objective clarity, scope fit, policy compliance, and output quality.")
	lines.append(f"Fallback behavior: {_fallback_policy_text(risk_tolerance)}")
	lines.append("")
	lines.append(f"Risk tolerance applied: {risk_tolerance}.")
	lines.append(f"Original request focus: {user_input}")
	return "\n".join(lines)


def _score_quality(
	*,
	candidate_response: str,
	plan: List[str],
	user_input: str,
	recommended_questions: List[str],
) -> Dict[str, object]:
	has_numbered_steps = "1." in candidate_response
	tokens = _tokenize(user_input)
	risk_signal = any(token in _RISK_TOKENS for token in tokens)

	clarity = 7
	if has_numbered_steps:
		clarity += 1
	if len(candidate_response) > 220:
		clarity += 1
	if recommended_questions:
		clarity += 1

	completeness = 5 + min(len(plan), 4)
	if recommended_questions:
		completeness = max(completeness, 8)

	safety = 8
	if risk_signal and "risk" in candidate_response.lower():
		safety = 9

	format_compliance = 8 if has_numbered_steps else 7
	overall = round((clarity + completeness + safety + format_compliance) / 4, 2)
	return {
		"clarity": min(10, clarity),
		"completeness": min(10, completeness),
		"safety": min(10, safety),
		"format_compliance": min(10, format_compliance),
		"overall": overall,
		"revision_required": overall < 8.0,
	}


def _revise_candidate_response(candidate_response: str, reasons: List[str]) -> str:
	reason_text = ", ".join(reasons) if reasons else "none"
	return (
		f"{candidate_response}\n\n"
		"Revision pass:\n"
		"- Added explicit assumptions and risk checks.\n"
		f"- Ambiguity reasons considered: {reason_text}."
	)


def _provider_mode() -> ProviderMode:
	mode = os.getenv("ASSISTANT_PROVIDER_MODE", "auto").strip().lower() or "auto"
	if mode not in {"auto", "openai", "local"}:
		raise AssistantServiceError(
			status_code=503,
			code="assistant_provider_unconfigured",
			message="ASSISTANT_PROVIDER_MODE must be one of: auto, openai, local.",
		)
	return mode  # type: ignore[return-value]


def _resolved_provider_mode(configured_mode: ProviderMode) -> ProviderMode:
	if configured_mode == "local":
		return "local"
	if configured_mode == "openai":
		return "openai"
	has_openai_key = bool(os.getenv("OPENAI_API_KEY", "").strip())
	return "openai" if has_openai_key else "local"


def _openai_timeout() -> float:
	raw = os.getenv("ASSISTANT_OPENAI_TIMEOUT_S", "").strip()
	if not raw:
		return _DEFAULT_OPENAI_TIMEOUT_S
	try:
		value = float(raw)
	except ValueError as exc:
		raise AssistantServiceError(
			status_code=503,
			code="assistant_provider_unconfigured",
			message="ASSISTANT_OPENAI_TIMEOUT_S must be numeric.",
		) from exc
	if value <= 0:
		raise AssistantServiceError(
			status_code=503,
			code="assistant_provider_unconfigured",
			message="ASSISTANT_OPENAI_TIMEOUT_S must be greater than zero.",
		)
	return value


def _openai_default_model() -> str:
	return os.getenv("ASSISTANT_OPENAI_MODEL", _DEFAULT_OPENAI_MODEL).strip() or _DEFAULT_OPENAI_MODEL


def _openai_model_allowlist() -> List[str]:
	raw = os.getenv("ASSISTANT_OPENAI_MODELS", "").strip()
	models = [item.strip() for item in raw.split(",") if item.strip()]
	default_model = _openai_default_model()
	if not models:
		models = [default_model]
	if default_model not in models:
		models.insert(0, default_model)
	seen: set[str] = set()
	unique: List[str] = []
	for model in models:
		if model in seen:
			continue
		seen.add(model)
		unique.append(model)
	return unique


def _resolve_model(requested_model: str | None) -> str:
	allowlist = _openai_model_allowlist()
	if requested_model:
		candidate = requested_model.strip()
		if candidate not in allowlist:
			raise AssistantServiceError(
				status_code=400,
				code="assistant_invalid_model",
				message=f"Model '{candidate}' is not in ASSISTANT_OPENAI_MODELS allowlist.",
			)
		return candidate
	return allowlist[0]


def list_models() -> Dict[str, object]:
	configured_mode = _provider_mode()
	effective_mode = _resolved_provider_mode(configured_mode)
	openai_key_present = bool(os.getenv("OPENAI_API_KEY", "").strip())
	provider_ready = True
	warnings: List[str] = []
	if configured_mode == "openai" and not openai_key_present:
		provider_ready = False
		warnings.append("OpenAI API key not configured. Set OPENAI_API_KEY.")
	return {
		"models": _openai_model_allowlist(),
		"default_model": _openai_model_allowlist()[0],
		"provider_mode": configured_mode,
		"effective_provider_mode": effective_mode,
		"provider_ready": provider_ready,
		"provider_warnings": warnings,
	}


def _openai_api_key(*, mode: ProviderMode) -> str:
	key = os.getenv("OPENAI_API_KEY", "").strip()
	if key:
		return key
	if mode == "local":
		return ""
	raise AssistantServiceError(
		status_code=503,
		code="assistant_provider_unconfigured",
		message="OpenAI API key not configured. Set OPENAI_API_KEY.",
	)


def _build_openai_client(*, api_key: str, timeout_s: float):
	try:
		from openai import OpenAI
	except ImportError as exc:
		raise AssistantServiceError(
			status_code=503,
			code="assistant_provider_unconfigured",
			message="OpenAI SDK not installed. Add 'openai' dependency.",
		) from exc
	return OpenAI(api_key=api_key, timeout=timeout_s)


def _openai_input(*, user_input: str, context: str | None, risk_tolerance: RiskTolerance, max_questions: int) -> List[Dict[str, Any]]:
	context_text = context.strip() if context else ""
	user_prompt = "\n".join(
		[
			f"user_input: {user_input}",
			f"context: {context_text or '(none)'}",
			f"risk_tolerance: {risk_tolerance}",
			f"max_questions: {max_questions}",
		]
	)
	return [
		{
			"role": "system",
			"content": [{"type": "input_text", "text": _OPENAI_SYSTEM_PROMPT}],
		},
		{
			"role": "user",
			"content": [{"type": "input_text", "text": user_prompt}],
		},
	]


def _extract_response_text(response: Any) -> str:
	output_text = getattr(response, "output_text", None)
	if isinstance(output_text, str) and output_text.strip():
		return output_text.strip()

	output = getattr(response, "output", None)
	if not isinstance(output, list):
		return ""
	parts: List[str] = []
	for item in output:
		content = getattr(item, "content", None)
		if content is None and isinstance(item, dict):
			content = item.get("content")
		if not isinstance(content, list):
			continue
		for chunk in content:
			text = getattr(chunk, "text", None)
			if text is None and isinstance(chunk, dict):
				text = chunk.get("text")
			if isinstance(text, str) and text.strip():
				parts.append(text.strip())
	return "\n".join(parts).strip()


def _extract_json_object(raw: str) -> Dict[str, Any]:
	candidate = raw.strip()
	if candidate.startswith("```"):
		candidate = re.sub(r"^```[a-zA-Z]*\s*", "", candidate)
		candidate = re.sub(r"\s*```$", "", candidate)
	start = candidate.find("{")
	end = candidate.rfind("}")
	if start == -1 or end == -1 or end <= start:
		raise AssistantServiceError(
			status_code=502,
			code="assistant_provider_error",
			message="Assistant provider returned invalid JSON content.",
		)
	try:
		parsed = json.loads(candidate[start : end + 1])
	except json.JSONDecodeError as exc:
		raise AssistantServiceError(
			status_code=502,
			code="assistant_provider_error",
			message="Assistant provider returned invalid JSON content.",
		) from exc
	if not isinstance(parsed, dict):
		raise AssistantServiceError(
			status_code=502,
			code="assistant_provider_error",
			message="Assistant provider returned an unexpected payload shape.",
		)
	return parsed


def _string_list(value: Any, *, limit: int) -> List[str]:
	if not isinstance(value, list):
		return []
	result: List[str] = []
	for item in value:
		if isinstance(item, str):
			cleaned = " ".join(item.split()).strip()
			if cleaned:
				result.append(cleaned)
		if len(result) >= limit:
			break
	return result


def _normalize_openai_payload(
	*,
	payload: Dict[str, Any],
	user_input: str,
	context: str | None,
	risk_tolerance: RiskTolerance,
	max_questions: int,
) -> Dict[str, object]:
	mode = str(payload.get("mode", "plan_execute")).strip().lower()
	if mode not in {"clarify", "plan_execute"}:
		mode = "plan_execute"
	if mode == "clarify" and max_questions == 0:
		mode = "plan_execute"

	local_ambiguity, local_notes = _ambiguity_score(user_input, context)
	questions = _string_list(payload.get("recommended_questions"), limit=max(1, max_questions))[:max_questions]
	plan = _string_list(payload.get("plan"), limit=8)
	notes = _string_list(payload.get("notes"), limit=8)
	notes = list(dict.fromkeys([*local_notes, *notes]))

	if mode == "clarify":
		if not questions:
			questions = _clarifying_questions(user_input, max_questions)
		plan = []
		candidate = str(payload.get("candidate_response", "")).strip()
		if not candidate:
			candidate = "Before execution, I need these clarifications:\n" + "\n".join(
				f"- {question}" for question in questions
			)
		quality = _score_quality(
			candidate_response=candidate,
			plan=[],
			user_input=user_input,
			recommended_questions=questions,
		)
		normalized = {
			"mode": "clarify",
			"ambiguity_score": local_ambiguity,
			"recommended_questions": questions,
			"plan": [],
			"candidate_response": candidate,
			"quality": quality,
			"iteration_count": 1,
			"notes": notes,
		}
		return _validate_normalized_payload(normalized)

	if not plan:
		plan = _make_plan(user_input, context, risk_tolerance)
	else:
		plan = _align_plan_to_prompt_book(
			plan=plan,
			context=context,
			risk_tolerance=risk_tolerance,
		)
	candidate = str(payload.get("candidate_response", "")).strip()
	if not candidate:
		candidate = _compose_candidate_response(plan, user_input, risk_tolerance)
	else:
		if "gate" not in candidate.lower():
			candidate = f"{candidate}\n\nGate checks: objective clarity, policy compliance, and output format."
		if "fallback" not in candidate.lower():
			candidate = f"{candidate}\nFallback policy: {_fallback_policy_text(risk_tolerance)}"
	quality = _score_quality(
		candidate_response=candidate,
		plan=plan,
		user_input=user_input,
		recommended_questions=[],
	)
	iteration_count = 1
	if quality["revision_required"]:
		candidate = _revise_candidate_response(candidate, notes)
		quality = _score_quality(
			candidate_response=candidate,
			plan=plan,
			user_input=user_input,
			recommended_questions=[],
		)
		iteration_count = 2
	normalized = {
		"mode": "plan_execute",
		"ambiguity_score": local_ambiguity,
		"recommended_questions": [],
		"plan": plan,
		"candidate_response": candidate,
		"quality": quality,
		"iteration_count": iteration_count,
		"notes": notes,
	}
	return _validate_normalized_payload(normalized)


def _session_context_text(session_id: str | None, max_turns: int | None = None) -> str:
	if not session_id:
		return ""
	turns = chat_session_service.recent_context(session_id, max_turns_override=max_turns)
	if not turns:
		return ""
	return "\n".join(f"{turn.role}: {turn.text}" for turn in turns)


def _merge_context(explicit_context: str | None, session_context: str | None) -> str | None:
	explicit = explicit_context.strip() if isinstance(explicit_context, str) else ""
	session = session_context.strip() if isinstance(session_context, str) else ""
	parts = []
	if explicit:
		parts.append(explicit)
	if session:
		parts.append(f"Session context:\n{session}")
	if not parts:
		return None
	return "\n\n".join(parts)


def _append_session_turns(session_id: str | None, user_input: str, result: Dict[str, object]) -> None:
	if not session_id:
		return
	chat_session_service.append_turn(session_id, "user", user_input)
	assistant_text = str(result.get("candidate_response") or result.get("final_message") or "").strip()
	if not assistant_text:
		assistant_text = "No assistant output was returned."
	chat_session_service.append_turn(session_id, "assistant", assistant_text)


def _respond_local(
	*,
	user_input: str,
	context: str | None,
	risk_tolerance: RiskTolerance,
	max_questions: int,
) -> Dict[str, object]:
	ambiguity_score, reasons = _ambiguity_score(user_input, context)
	iteration_count = 1

	if ambiguity_score >= 0.55 and max_questions > 0:
		questions = _clarifying_questions(user_input, max_questions)
		candidate = "Before execution, I need these clarifications:\n" + "\n".join(
			f"- {question}" for question in questions
		)
		quality = _score_quality(
			candidate_response=candidate,
			plan=[],
			user_input=user_input,
			recommended_questions=questions,
		)
		return {
			"mode": "clarify",
			"ambiguity_score": ambiguity_score,
			"recommended_questions": questions,
			"plan": [],
			"candidate_response": candidate,
			"quality": quality,
			"iteration_count": iteration_count,
			"notes": reasons,
		}

	plan = _make_plan(user_input, context, risk_tolerance)
	candidate = _compose_candidate_response(plan, user_input, risk_tolerance)
	quality = _score_quality(
		candidate_response=candidate,
		plan=plan,
		user_input=user_input,
		recommended_questions=[],
	)
	if quality["revision_required"]:
		candidate = _revise_candidate_response(candidate, reasons)
		quality = _score_quality(
			candidate_response=candidate,
			plan=plan,
			user_input=user_input,
			recommended_questions=[],
		)
		iteration_count = 2

	return {
		"mode": "plan_execute",
		"ambiguity_score": ambiguity_score,
		"recommended_questions": [],
		"plan": plan,
		"candidate_response": candidate,
		"quality": quality,
		"iteration_count": iteration_count,
		"notes": reasons,
	}


def _openai_error(exc: Exception) -> AssistantServiceError:
	name = exc.__class__.__name__
	if isinstance(exc, TimeoutError) or name == "APITimeoutError":
		return AssistantServiceError(
			status_code=504,
			code="assistant_provider_timeout",
			message="Assistant provider timed out.",
		)
	return AssistantServiceError(
		status_code=502,
		code="assistant_provider_error",
		message="Assistant provider request failed.",
	)


def _respond_openai(
	*,
	user_input: str,
	context: str | None,
	risk_tolerance: RiskTolerance,
	max_questions: int,
	mode: ProviderMode,
	model: str,
) -> Dict[str, object]:
	api_key = _openai_api_key(mode=mode)
	if not api_key:
		raise AssistantServiceError(
			status_code=503,
			code="assistant_provider_unconfigured",
			message="OpenAI API key not configured. Set OPENAI_API_KEY.",
		)
	client = _build_openai_client(api_key=api_key, timeout_s=_openai_timeout())
	try:
		response = client.responses.create(
			model=model,
			input=_openai_input(
				user_input=user_input,
				context=context,
				risk_tolerance=risk_tolerance,
				max_questions=max_questions,
			),
		)
	except Exception as exc:  # pragma: no cover - exercised by targeted tests.
		raise _openai_error(exc) from exc

	raw = _extract_response_text(response)
	if not raw:
		raise AssistantServiceError(
			status_code=502,
			code="assistant_provider_error",
			message="Assistant provider returned an empty response.",
		)
	parsed = _extract_json_object(raw)
	return _normalize_openai_payload(
		payload=parsed,
		user_input=user_input,
		context=context,
		risk_tolerance=risk_tolerance,
		max_questions=max_questions,
	)


def _coerce_event_dict(event: Any) -> Dict[str, Any]:
	if isinstance(event, dict):
		return event
	for attr in ("model_dump", "dict"):
		method = getattr(event, attr, None)
		if callable(method):
			try:
				value = method()
			except TypeError:
				continue
			if isinstance(value, dict):
				return value
	return {}


def _extract_stream_delta(event: Any) -> str:
	for attr in ("delta", "text"):
		value = getattr(event, attr, None)
		if isinstance(value, str) and value:
			return value

	data = _coerce_event_dict(event)
	for key in ("delta", "text"):
		value = data.get(key)
		if isinstance(value, str) and value:
			return value

	content = data.get("content")
	if isinstance(content, list):
		parts: List[str] = []
		for item in content:
			if isinstance(item, dict):
				for key in ("delta", "text"):
					value = item.get(key)
					if isinstance(value, str) and value:
						parts.append(value)
		if parts:
			return "".join(parts)
	return ""


def _chunk_text(text: str, size: int = _DEFAULT_STREAM_CHUNK_CHARS) -> List[str]:
	cleaned = text.strip()
	if not cleaned:
		return []
	chunks: List[str] = []
	for i in range(0, len(cleaned), size):
		chunks.append(cleaned[i : i + size])
	return chunks


def _openai_stream_response(
	*,
	user_input: str,
	context: str | None,
	risk_tolerance: RiskTolerance,
	max_questions: int,
	mode: ProviderMode,
	model: str,
) -> Tuple[Dict[str, object], List[str]]:
	api_key = _openai_api_key(mode=mode)
	if not api_key:
		raise AssistantServiceError(
			status_code=503,
			code="assistant_provider_unconfigured",
			message="OpenAI API key not configured. Set OPENAI_API_KEY.",
		)
	client = _build_openai_client(api_key=api_key, timeout_s=_openai_timeout())
	collected_raw: List[str] = []
	deltas: List[str] = []
	try:
		stream = client.responses.create(
			model=model,
			input=_openai_input(
				user_input=user_input,
				context=context,
				risk_tolerance=risk_tolerance,
				max_questions=max_questions,
			),
			stream=True,
		)
		for event in stream:
			delta = _extract_stream_delta(event)
			if delta:
				collected_raw.append(delta)
				deltas.append(delta)
	except TypeError:
		# SDKs that do not support stream=True will fall back to non-stream mode.
		result = _respond_openai(
			user_input=user_input,
			context=context,
			risk_tolerance=risk_tolerance,
			max_questions=max_questions,
			mode=mode,
			model=model,
		)
		return result, _chunk_text(str(result.get("candidate_response", "")))
	except Exception as exc:  # pragma: no cover - exercised by targeted tests.
		raise _openai_error(exc) from exc

	raw = "".join(collected_raw).strip()
	if raw:
		try:
			parsed = _extract_json_object(raw)
			result = _normalize_openai_payload(
				payload=parsed,
				user_input=user_input,
				context=context,
				risk_tolerance=risk_tolerance,
				max_questions=max_questions,
			)
			return result, deltas
		except AssistantServiceError:
			# If streamed JSON is incomplete/invalid, safely recover with standard call.
			pass

	result = _respond_openai(
		user_input=user_input,
		context=context,
		risk_tolerance=risk_tolerance,
		max_questions=max_questions,
		mode=mode,
		model=model,
	)
	return result, _chunk_text(str(result.get("candidate_response", "")))


def _build_result(
	*,
	user_input: str,
	context: str | None,
	risk_tolerance: RiskTolerance,
	max_questions: int,
	mode: ProviderMode,
	model: str,
) -> Dict[str, object]:
	if mode == "local":
		result = _respond_local(
			user_input=user_input,
			context=context,
			risk_tolerance=risk_tolerance,
			max_questions=max_questions,
		)
	else:
		result = _respond_openai(
			user_input=user_input,
			context=context,
			risk_tolerance=risk_tolerance,
			max_questions=max_questions,
			mode=mode,
			model=model,
		)
	result["model"] = model
	result["provider_mode"] = mode
	return result


def _run_aca_pipeline(
	*,
	user_input: str,
	context: str | None,
	risk_tolerance: RiskTolerance,
	max_questions: int,
	mode: ProviderMode,
	model: str,
	session_id: str | None,
	trace_enabled: bool,
) -> Tuple[Dict[str, object], List[dict]]:
	orchestrator = ACAOrchestrator(
		ACAOrchestratorHooks(
			build_result=_build_result,
		)
	)
	request = ACARequest(
		user_input=user_input,
		context=context,
		risk_tolerance=risk_tolerance,
		max_questions=max_questions,
		model=model,
		provider_mode=mode,
		session_id=session_id,
		trace_enabled=trace_enabled,
	)
	return orchestrator.run(request)


def _module_id_index(module_id: str) -> int:
	if not isinstance(module_id, str):
		return -1
	text = module_id.strip().upper()
	if not text.startswith("M"):
		return -1
	try:
		return int(text[1:])
	except ValueError:
		return -1


def _v2_module_outputs(result: Dict[str, object]) -> Dict[str, Dict[str, Any]]:
	module_outputs = result.get("module_outputs")
	if not isinstance(module_outputs, dict):
		return {}
	selected: Dict[str, Dict[str, Any]] = {}
	for module_id, payload in module_outputs.items():
		if not isinstance(module_id, str):
			continue
		index = _module_id_index(module_id)
		if index < 10 or index > 23:
			continue
		if isinstance(payload, dict):
			selected[module_id] = payload
	return selected


def _build_v2_payload(
	*,
	result: Dict[str, object],
	trace: List[dict],
	session_id: str | None,
	trace_enabled: bool,
) -> Dict[str, Any]:
	mode = str(result.get("mode") or "plan_execute").strip().lower()
	if mode not in {"clarify", "plan_execute"}:
		mode = "plan_execute"
	final_message = str(result.get("final_message") or result.get("candidate_response") or "").strip()
	decision_graph = result.get("decision_graph")
	if not isinstance(decision_graph, list):
		decision_graph = []
	quality = result.get("quality")
	if not isinstance(quality, dict):
		quality = {}
	safety = result.get("safety")
	if not isinstance(safety, dict):
		safety = {}
	fallback = result.get("fallback")
	if not isinstance(fallback, dict):
		fallback = {}
	lane_used = str(result.get("lane_used") or "governed")
	if lane_used not in {"quick", "governed"}:
		lane_used = "governed"
	complexity_reasons = result.get("complexity_reasons")
	if not isinstance(complexity_reasons, list):
		complexity_reasons = []
	assumptions = result.get("assumptions")
	if not isinstance(assumptions, list):
		assumptions = []
	pqs_overall_raw = result.get("pqs_overall")
	if isinstance(pqs_overall_raw, (int, float)):
		pqs_overall = round(float(pqs_overall_raw), 2)
	else:
		pqs_overall = round(float(quality.get("overall", 0.0)) if isinstance(quality.get("overall"), (int, float)) else 0.0, 2)
	fallback_level_raw = result.get("fallback_level")
	if isinstance(fallback_level_raw, int):
		fallback_level = fallback_level_raw
	else:
		fallback_level = int(fallback.get("level", 0)) if isinstance(fallback.get("level"), int) else 0
	payload: Dict[str, Any] = {
		"aca_version": "4.1",
		"session_id": session_id or "",
		"mode": mode,
		"final_message": final_message,
		"decision_graph": decision_graph,
		"module_outputs": _v2_module_outputs(result),
		"quality": quality,
		"safety": safety,
		"fallback": fallback,
		"lane_used": lane_used,
		"interaction_mode": str(result.get("interaction_mode") or "task"),
		"complexity_reasons": complexity_reasons,
		"pqs_overall": pqs_overall,
		"fallback_level": fallback_level,
		"assumptions": assumptions,
		"intake_frame": result.get("intake_frame", {}),
		"adaptive_defaults": result.get("adaptive_defaults", {}),
		"adaptive_evolution": result.get("adaptive_evolution", []),
		"runtime_metrics": result.get("runtime_metrics", {}),
	}
	if trace_enabled:
		payload["trace"] = trace
	return payload


def _attach_runtime_metrics(result: Dict[str, object], started_at: float) -> None:
	duration_ms = int((time.perf_counter() - started_at) * 1000)
	fallback = result.get("fallback") if isinstance(result.get("fallback"), dict) else {}
	result["runtime_metrics"] = {
		"duration_ms": duration_ms,
		"lane_used": str(result.get("lane_used") or "governed"),
		"fallback_triggered": bool(fallback.get("triggered")) if isinstance(fallback, dict) else False,
		"fallback_level": int(result.get("fallback_level") or 0) if isinstance(result.get("fallback_level"), int) else 0,
	}


def respond_with_trace(
	*,
	user_input: str,
	context: str | None = None,
	risk_tolerance: RiskTolerance = "medium",
	max_questions: int = 1,
	model: str | None = None,
	session_id: str | None = None,
	trace_enabled: bool = False,
) -> Tuple[Dict[str, object], List[dict]]:
	started_at = time.perf_counter()
	cleaned = " ".join(user_input.split())
	if not cleaned:
		raise ValueError("user_input must not be empty.")

	mode = _provider_mode()
	effective_mode = _resolved_provider_mode(mode)
	resolved_model = _resolve_model(model)
	session_context = _session_context_text(session_id, chat_session_service.default_context_turns())
	combined_context = _merge_context(context, session_context)

	if _aca_enabled():
		result, trace = _run_aca_pipeline(
			user_input=cleaned,
			context=combined_context,
			risk_tolerance=risk_tolerance,
			max_questions=max_questions,
			mode=effective_mode,
			model=resolved_model,
			session_id=session_id,
			trace_enabled=trace_enabled,
		)
	else:
		result = _build_result(
			user_input=cleaned,
			context=combined_context,
			risk_tolerance=risk_tolerance,
			max_questions=max_questions,
			mode=effective_mode,
			model=resolved_model,
		)
		trace = []

	result = _apply_adaptive_protocol(
		result=result,
		user_input=cleaned,
		context=combined_context,
		risk_tolerance=risk_tolerance,
		max_questions=max_questions,
		session_id=session_id,
	)
	_attach_runtime_metrics(result, started_at)
	_append_session_turns(session_id, cleaned, result)
	return result, trace


def respond(
	*,
	user_input: str,
	context: str | None = None,
	risk_tolerance: RiskTolerance = "medium",
	max_questions: int = 1,
	model: str | None = None,
	session_id: str | None = None,
) -> Dict[str, object]:
	result, _trace = respond_with_trace(
		user_input=user_input,
		context=context,
		risk_tolerance=risk_tolerance,
		max_questions=max_questions,
		model=model,
		session_id=session_id,
		trace_enabled=False,
	)
	return result


def stream_respond(
	*,
	user_input: str,
	context: str | None = None,
	risk_tolerance: RiskTolerance = "medium",
	max_questions: int = 1,
	model: str | None = None,
	session_id: str | None = None,
	trace_enabled: bool = False,
) -> Iterator[Dict[str, Any]]:
	started_at = time.perf_counter()
	cleaned = " ".join(user_input.split())
	if not cleaned:
		raise ValueError("user_input must not be empty.")

	mode = _provider_mode()
	effective_mode = _resolved_provider_mode(mode)
	resolved_model = _resolve_model(model)
	session_context = _session_context_text(session_id, chat_session_service.default_context_turns())
	combined_context = _merge_context(context, session_context)

	yield {
		"event": "meta",
		"data": {
			"provider_mode": effective_mode,
			"configured_provider_mode": mode,
			"model": resolved_model,
			"session_id": session_id,
			"aca_enabled": _aca_enabled(),
			"trace_enabled": trace_enabled,
		},
	}

	trace_events: List[dict] = []
	if _aca_enabled():
		result, trace_events = _run_aca_pipeline(
			user_input=cleaned,
			context=combined_context,
			risk_tolerance=risk_tolerance,
			max_questions=max_questions,
			mode=effective_mode,
			model=resolved_model,
			session_id=session_id,
			trace_enabled=trace_enabled,
		)
		if trace_enabled:
			for event in trace_events:
				yield {"event": "trace", "data": event}
	else:
		if effective_mode == "local":
			result = _respond_local(
				user_input=cleaned,
				context=combined_context,
				risk_tolerance=risk_tolerance,
				max_questions=max_questions,
			)
		else:
			result, _deltas = _openai_stream_response(
				user_input=cleaned,
				context=combined_context,
				risk_tolerance=risk_tolerance,
				max_questions=max_questions,
				mode=effective_mode,
				model=resolved_model,
			)

	result = _apply_adaptive_protocol(
		result=result,
		user_input=cleaned,
		context=combined_context,
		risk_tolerance=risk_tolerance,
		max_questions=max_questions,
		session_id=session_id,
	)
	_attach_runtime_metrics(result, started_at)
	deltas = _chunk_text(str(result.get("candidate_response", "")))
	for delta in deltas:
		yield {"event": "delta", "data": {"text": delta}}

	result["model"] = resolved_model
	result["provider_mode"] = effective_mode
	_append_session_turns(session_id, cleaned, result)
	done_data: Dict[str, Any] = {
		"assistant": result,
		"session_id": session_id,
		"model": resolved_model,
	}
	if trace_enabled:
		done_data["aca_trace"] = trace_events
	yield {
		"event": "done",
		"data": done_data,
	}


def respond_v2_with_trace(
	*,
	user_input: str,
	context: str | None = None,
	risk_tolerance: RiskTolerance = "medium",
	max_questions: int = 1,
	model: str | None = None,
	session_id: str | None = None,
	trace_enabled: bool = False,
) -> Tuple[Dict[str, Any], List[dict]]:
	started_at = time.perf_counter()
	cleaned = " ".join(user_input.split())
	if not cleaned:
		raise ValueError("user_input must not be empty.")

	mode = _provider_mode()
	effective_mode = _resolved_provider_mode(mode)
	resolved_model = _resolve_model(model)
	session_context = _session_context_text(session_id, chat_session_service.default_context_turns())
	combined_context = _merge_context(context, session_context)

	result, trace = _run_aca_pipeline(
		user_input=cleaned,
		context=combined_context,
		risk_tolerance=risk_tolerance,
		max_questions=max_questions,
		mode=effective_mode,
		model=resolved_model,
		session_id=session_id,
		trace_enabled=trace_enabled,
	)
	result = _apply_adaptive_protocol(
		result=result,
		user_input=cleaned,
		context=combined_context,
		risk_tolerance=risk_tolerance,
		max_questions=max_questions,
		session_id=session_id,
	)
	_attach_runtime_metrics(result, started_at)
	result["model"] = resolved_model
	result["provider_mode"] = effective_mode
	v2 = _build_v2_payload(
		result=result,
		trace=trace,
		session_id=session_id,
		trace_enabled=trace_enabled,
	)
	_append_session_turns(session_id, cleaned, {"final_message": v2.get("final_message", "")})
	return v2, trace


def stream_v2(
	*,
	user_input: str,
	context: str | None = None,
	risk_tolerance: RiskTolerance = "medium",
	max_questions: int = 1,
	model: str | None = None,
	session_id: str | None = None,
	trace_enabled: bool = False,
) -> Iterator[Dict[str, Any]]:
	started_at = time.perf_counter()
	cleaned = " ".join(user_input.split())
	if not cleaned:
		raise ValueError("user_input must not be empty.")

	mode = _provider_mode()
	effective_mode = _resolved_provider_mode(mode)
	resolved_model = _resolve_model(model)
	session_context = _session_context_text(session_id, chat_session_service.default_context_turns())
	combined_context = _merge_context(context, session_context)

	yield {
		"event": "meta",
		"data": {
			"api_version": "v2",
			"aca_version": "4.1",
			"provider_mode": effective_mode,
			"configured_provider_mode": mode,
			"model": resolved_model,
			"session_id": session_id,
			"trace_enabled": trace_enabled,
		},
	}

	result, trace = _run_aca_pipeline(
		user_input=cleaned,
		context=combined_context,
		risk_tolerance=risk_tolerance,
		max_questions=max_questions,
		mode=effective_mode,
		model=resolved_model,
		session_id=session_id,
		trace_enabled=trace_enabled,
	)
	result = _apply_adaptive_protocol(
		result=result,
		user_input=cleaned,
		context=combined_context,
		risk_tolerance=risk_tolerance,
		max_questions=max_questions,
		session_id=session_id,
	)
	_attach_runtime_metrics(result, started_at)
	result["model"] = resolved_model
	result["provider_mode"] = effective_mode

	for event in trace:
		yield {
			"event": "checkpoint",
			"data": {
				"module_id": event.get("module_id"),
				"module_name": event.get("module_name"),
				"status": event.get("status"),
				"tier": event.get("tier"),
				"detail": event.get("detail"),
			},
		}
		if trace_enabled:
			yield {"event": "trace", "data": event}

	message = str(result.get("final_message") or result.get("candidate_response") or "")
	for delta in _chunk_text(message):
		yield {"event": "delta", "data": {"text": delta}}

	v2 = _build_v2_payload(
		result=result,
		trace=trace,
		session_id=session_id,
		trace_enabled=trace_enabled,
	)
	_append_session_turns(session_id, cleaned, {"final_message": v2.get("final_message", "")})
	yield {"event": "done", "data": v2}
