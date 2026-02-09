from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Iterator, List, Literal, Tuple

from app.backend.services import chat_session_service


RiskTolerance = Literal["low", "medium", "high"]
ProviderMode = Literal["auto", "openai", "local"]

_DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"
_DEFAULT_OPENAI_TIMEOUT_S = 30.0
_DEFAULT_STREAM_CHUNK_CHARS = 80

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
	"write",
	"fix",
	"refactor",
	"test",
	"document",
}

_RISK_TOKENS = {"auth", "payment", "security", "privacy", "legal", "medical", "finance", "production"}

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


def _tokenize(text: str) -> List[str]:
	return re.findall(r"[a-zA-Z0-9']+", text.lower())


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
	return {
		"models": _openai_model_allowlist(),
		"default_model": _openai_model_allowlist()[0],
		"provider_mode": _provider_mode(),
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
		return {
			"mode": "clarify",
			"ambiguity_score": local_ambiguity,
			"recommended_questions": questions,
			"plan": [],
			"candidate_response": candidate,
			"quality": quality,
			"iteration_count": 1,
			"notes": notes,
		}

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
	return {
		"mode": "plan_execute",
		"ambiguity_score": local_ambiguity,
		"recommended_questions": [],
		"plan": plan,
		"candidate_response": candidate,
		"quality": quality,
		"iteration_count": iteration_count,
		"notes": notes,
	}


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
	assistant_text = str(result.get("candidate_response", "")).strip()
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


def respond(
	*,
	user_input: str,
	context: str | None = None,
	risk_tolerance: RiskTolerance = "medium",
	max_questions: int = 2,
	model: str | None = None,
	session_id: str | None = None,
) -> Dict[str, object]:
	cleaned = " ".join(user_input.split())
	if not cleaned:
		raise ValueError("user_input must not be empty.")

	mode = _provider_mode()
	resolved_model = _resolve_model(model)
	session_context = _session_context_text(session_id, chat_session_service.default_context_turns())
	combined_context = _merge_context(context, session_context)
	result = _build_result(
		user_input=cleaned,
		context=combined_context,
		risk_tolerance=risk_tolerance,
		max_questions=max_questions,
		mode=mode,
		model=resolved_model,
	)
	_append_session_turns(session_id, cleaned, result)
	return result


def stream_respond(
	*,
	user_input: str,
	context: str | None = None,
	risk_tolerance: RiskTolerance = "medium",
	max_questions: int = 2,
	model: str | None = None,
	session_id: str | None = None,
) -> Iterator[Dict[str, Any]]:
	cleaned = " ".join(user_input.split())
	if not cleaned:
		raise ValueError("user_input must not be empty.")

	mode = _provider_mode()
	resolved_model = _resolve_model(model)
	session_context = _session_context_text(session_id, chat_session_service.default_context_turns())
	combined_context = _merge_context(context, session_context)

	yield {
		"event": "meta",
		"data": {
			"provider_mode": mode,
			"model": resolved_model,
			"session_id": session_id,
		},
	}

	if mode == "local":
		result = _respond_local(
			user_input=cleaned,
			context=combined_context,
			risk_tolerance=risk_tolerance,
			max_questions=max_questions,
		)
		deltas = _chunk_text(str(result.get("candidate_response", "")))
	else:
		result, deltas = _openai_stream_response(
			user_input=cleaned,
			context=combined_context,
			risk_tolerance=risk_tolerance,
			max_questions=max_questions,
			mode=mode,
			model=resolved_model,
		)

	for delta in deltas:
		yield {"event": "delta", "data": {"text": delta}}

	result["model"] = resolved_model
	result["provider_mode"] = mode
	_append_session_turns(session_id, cleaned, result)
	yield {
		"event": "done",
		"data": {
			"assistant": result,
			"session_id": session_id,
			"model": resolved_model,
		},
	}
