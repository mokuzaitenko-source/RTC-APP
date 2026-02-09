from __future__ import annotations

from app.backend.aca.trace import make_event
from app.backend.aca.types import ACAState


def run_task_integrity_stub(state: ACAState) -> None:
	state.trace.append(
		make_event(
			module_id="M18",
			module_name="TaskIntegrityStub",
			tier="tier3_operational",
			status="stub",
			detail="Task Integrity layer is running as a placeholder in this release.",
		)
	)


def run_error_coherence_stub(state: ACAState) -> None:
	state.trace.append(
		make_event(
			module_id="M19",
			module_name="ErrorCoherenceStub",
			tier="tier3_operational",
			status="stub",
			detail="Error and Coherence checker is running as a placeholder in this release.",
		)
	)


def run_fallback_manager_stub(state: ACAState) -> None:
	state.trace.append(
		make_event(
			module_id="M20",
			module_name="FallbackManagerStub",
			tier="tier3_operational",
			status="stub",
			detail="Fallback Manager is running as a placeholder in this release.",
		)
	)
	notes = state.result.get("notes")
	if isinstance(notes, list):
		for marker in ("ACA module 18 running in stub mode.", "ACA module 19 running in stub mode.", "ACA module 20 running in stub mode."):
			if marker not in notes:
				notes.append(marker)

