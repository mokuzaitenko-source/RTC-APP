from __future__ import annotations

import re
from typing import Dict, List


_PROMPT_INJECTION_PATTERNS = [
	r"ignore (all|previous|prior) instructions",
	r"reveal (the )?(system|developer) prompt",
	r"bypass (safety|policy|guardrails?)",
	r"disable (safety|guardrails?)",
	r"act as (a )?jailbreak",
	r"tool call",
]

_UNTRUSTED_TOOL_OUTPUT_PATTERNS = [
	r"tool output: .*ignore",
	r"retrieved content: .*override",
	r"search result: .*run this command",
	r"function result: .*exfiltrate",
]

_SENSITIVE_TEXT_PATTERNS: List[tuple[str, str]] = [
	(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[redacted_email]"),
	(r"\b\d{3}-\d{2}-\d{4}\b", "[redacted_ssn]"),
	(r"\b(?:\d[ -]?){13,19}\b", "[redacted_card]"),
	(r"\bsk-[A-Za-z0-9]{16,}\b", "[redacted_key]"),
	(r"\b(?:\+?1[ -]?)?\(?\d{3}\)?[ -]?\d{3}[ -]?\d{4}\b", "[redacted_phone]"),
]

_FORBIDDEN_MEMORY_PATTERNS = [
	r"chain[- ]of[- ]thought",
	r"internal reasoning",
	r"agent trace",
	r"system prompt",
]

_UNSAFE_OUTPUT_PATTERNS = [
	r"how to make a bomb",
	r"commit fraud",
	r"steal credentials",
]


def detect_prompt_injection(text: str) -> bool:
	content = text.lower()
	return any(re.search(pattern, content, re.IGNORECASE) for pattern in _PROMPT_INJECTION_PATTERNS)


def detect_untrusted_tool_instruction(text: str) -> bool:
	content = text.lower()
	return any(re.search(pattern, content, re.IGNORECASE) for pattern in _UNTRUSTED_TOOL_OUTPUT_PATTERNS)


def sanitize_memory_text(text: str, *, max_chars: int = 4000) -> str:
	result = text
	for pattern, replacement in _SENSITIVE_TEXT_PATTERNS:
		result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
	for pattern in _FORBIDDEN_MEMORY_PATTERNS:
		result = re.sub(pattern, "[redacted_internal]", result, flags=re.IGNORECASE)
	result = " ".join(result.split()).strip()
	if len(result) > max_chars:
		result = result[: max_chars - 15].rstrip() + "...[truncated]"
	return result


def memory_write_allowed(payload: str) -> bool:
	text = payload.lower()
	return not any(re.search(pattern, text, re.IGNORECASE) for pattern in _FORBIDDEN_MEMORY_PATTERNS)


def filter_safe_metadata(metadata: Dict[str, object]) -> Dict[str, object]:
	allowed = {"tone_preference", "pacing_preference", "structural_preference", "verbosity_level", "theme", "font_size"}
	return {key: value for key, value in metadata.items() if key in allowed}


def output_is_safe(text: str) -> bool:
	content = text.lower()
	return not any(re.search(pattern, content, re.IGNORECASE) for pattern in _UNSAFE_OUTPUT_PATTERNS)
