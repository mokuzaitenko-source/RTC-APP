from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Dict, List


_DEFAULT_TTL_SECONDS = 6 * 60 * 60
_DEFAULT_MAX_TURNS = 80
_DEFAULT_CONTEXT_TURNS = 12


@dataclass
class ChatTurn:
	role: str
	text: str
	created_at: str


@dataclass
class ChatSession:
	session_id: str
	updated_at: str
	turns: List[ChatTurn] = field(default_factory=list)


_STORE: Dict[str, ChatSession] = {}
_LOCK = Lock()


def _now() -> datetime:
	return datetime.now(timezone.utc)


def _now_iso() -> str:
	return _now().isoformat().replace("+00:00", "Z")


def _int_env(name: str, default: int, minimum: int = 1) -> int:
	raw = os.getenv(name, "").strip()
	if not raw:
		return default
	try:
		value = int(raw)
	except ValueError:
		return default
	return value if value >= minimum else default


def ttl_seconds() -> int:
	return _int_env("ASSISTANT_SESSION_TTL_S", _DEFAULT_TTL_SECONDS, minimum=60)


def max_turns() -> int:
	return _int_env("ASSISTANT_SESSION_MAX_TURNS", _DEFAULT_MAX_TURNS, minimum=10)


def default_context_turns() -> int:
	return _int_env("ASSISTANT_SESSION_CONTEXT_TURNS", _DEFAULT_CONTEXT_TURNS, minimum=1)


def _evict_expired_locked() -> None:
	now = _now()
	ttl = timedelta(seconds=ttl_seconds())
	expired: List[str] = []
	for session_id, session in _STORE.items():
		try:
			updated = datetime.fromisoformat(session.updated_at.replace("Z", "+00:00"))
		except ValueError:
			expired.append(session_id)
			continue
		if now - updated > ttl:
			expired.append(session_id)
	for session_id in expired:
		_STORE.pop(session_id, None)


def ensure_session(session_id: str) -> ChatSession:
	with _LOCK:
		_evict_expired_locked()
		session = _STORE.get(session_id)
		if session is None:
			session = ChatSession(session_id=session_id, updated_at=_now_iso(), turns=[])
			_STORE[session_id] = session
		return session


def append_turn(session_id: str, role: str, text: str) -> ChatSession:
	cleaned = " ".join(text.split()).strip()
	if not cleaned:
		return ensure_session(session_id)
	role_clean = "assistant" if role == "assistant" else "user"
	with _LOCK:
		_evict_expired_locked()
		session = _STORE.get(session_id)
		if session is None:
			session = ChatSession(session_id=session_id, updated_at=_now_iso(), turns=[])
			_STORE[session_id] = session
		session.turns.append(ChatTurn(role=role_clean, text=cleaned, created_at=_now_iso()))
		session.turns = session.turns[-max_turns() :]
		session.updated_at = _now_iso()
		return session


def recent_context(session_id: str, max_turns_override: int | None = None) -> List[ChatTurn]:
	with _LOCK:
		_evict_expired_locked()
		session = _STORE.get(session_id)
		if session is None:
			return []
		limit = max_turns_override if isinstance(max_turns_override, int) and max_turns_override > 0 else default_context_turns()
		return list(session.turns[-limit:])

