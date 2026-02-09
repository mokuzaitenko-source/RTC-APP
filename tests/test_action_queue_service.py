from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from app.backend import constants
from app.backend.adapters import sqlite_adapter
from app.backend.services.action_queue_service import build_action_queue
from app.backend.validators.types import InvariantResult, ValidatorContext, ValidatorReport


def _report(status_overrides: dict[str, str]) -> ValidatorReport:
	invariants = []
	for invariant_id in constants.INVARIANT_ORDER:
		status = status_overrides.get(invariant_id, "pass")
		invariants.append(
			InvariantResult(
				id=invariant_id,
				status=status,
				message=f"{invariant_id} is {status}",
				evidence=[],
				recommended_action=f"fix_{invariant_id}",
			)
		)
	now = datetime.now(timezone.utc)
	report_status = "fail" if any(inv.status == "fail" for inv in invariants) else "pass"
	return ValidatorReport(
		run_id="run-test",
		run_type="validate",
		status=report_status,
		started_at=now,
		ended_at=now,
		invariants=invariants,
		summary="test",
	)


def _matrix_text(rows: list[tuple[str, str, str, str]]) -> str:
	head = (
		"| Req ID | Requirement | Source | Status | Finding | Enforcement Point | Test | Telemetry Proof |\n"
		"| --- | --- | --- | --- | --- | --- | --- | --- |\n"
	)
	lines = []
	for req_id, source_ref, status, finding in rows:
		lines.append(
			f"| {req_id} | Requirement {req_id} | {source_ref} | {status} | {finding} | TBD | TBD | TBD |"
		)
	return head + "\n".join(lines) + "\n"


class ActionQueueTests(TestCase):
	def test_toolchain_fail_returns_only_tier0_cards(self) -> None:
		report = _report({"toolchain_ok": "fail"})
		actions = build_action_queue(report)
		self.assertEqual([action["tier"] for action in actions], [0, 0])
		self.assertEqual([action["type"] for action in actions], ["run_sync", "run_validate"])
		for action in actions:
			self.assertTrue(action["commands"])
			self.assertTrue(action["links"])

	def test_wave1_then_ready_then_invariant_order(self) -> None:
		with TemporaryDirectory() as tmpdir:
			root = Path(tmpdir)
			rfc_path = root / "rfc.md"
			matrix_path = root / "matrix.md"
			playbook_path = root / "playbook.md"
			handoff_path = root / "handoff.md"
			db_path = root / "state.db"

			rfc_path.write_text(
				"## 4.1\nThis MUST be mapped.\n## 6.2\nThis SHOULD be tracked.\n",
				encoding="utf-8",
			)
			matrix_path.write_text(
				_matrix_text(
					[
						("R-4.1-01", "RFC 4.1:L2", "gap", "F-001"),
						("R-6.2-01", "RFC 6.2:L4", "partial", "F-010"),
					]
				),
				encoding="utf-8",
			)
			playbook_path.write_text(
				"## Wave 1\n### F-001\nImpacted Requirement IDs:\n- `R-4.1-01`\n"
				"Dependencies:\n- `F-010`\n\n## Wave 2\n### F-010\nImpacted Requirement IDs:\n"
				"- `R-6.2-01`\nDependencies:\n- `F-001`\n",
				encoding="utf-8",
			)
			handoff_path.write_text("# handoff\n", encoding="utf-8")

			sqlite_adapter.init_db(str(db_path))
			sqlite_adapter.upsert_finding_state(
				finding_id="F-010",
				status="ready_for_validation",
				note=None,
				db_path=str(db_path),
			)

			report = _report({"parity": "fail"})
			with patch.object(constants, "DEFAULT_RFC_PATH", str(rfc_path)), patch.object(
				constants, "DEFAULT_MATRIX_PATH", str(matrix_path)
			), patch.object(constants, "DEFAULT_PLAYBOOK_PATH", str(playbook_path)), patch.object(
				constants, "DEFAULT_HANDOFF_PATH", str(handoff_path)
			), patch.object(
				constants, "DEFAULT_DB_PATH", str(db_path)
			):
				actions = build_action_queue(report)

		tiers = [action["tier"] for action in actions[:3]]
		self.assertEqual(tiers, [1, 2, 3])
		self.assertEqual(actions[0]["target"], "F-001")
		self.assertEqual(actions[1]["type"], "run_validate")
		self.assertEqual(actions[2]["target"], "parity")
		for action in actions[:3]:
			self.assertTrue(action["commands"])
			self.assertTrue(action["links"])

	def test_f016_triage_batches_by_section_density(self) -> None:
		with TemporaryDirectory() as tmpdir:
			root = Path(tmpdir)
			rfc_path = root / "rfc.md"
			matrix_path = root / "matrix.md"
			playbook_path = root / "playbook.md"
			handoff_path = root / "handoff.md"
			db_path = root / "state.db"

			rfc_path.write_text(
				"## 6.2\nThis SHOULD be triaged.\n## 5.1\nThis MAY be triaged.\n",
				encoding="utf-8",
			)
			matrix_path.write_text(
				_matrix_text(
					[
						("R-6.2-01", "RFC 6.2:L2", "gap", "F-016"),
						("R-6.2-02", "RFC 6.2:L2", "partial", "F-016"),
						("R-5.1-01", "RFC 5.1:L4", "gap", "F-016"),
					]
				),
				encoding="utf-8",
			)
			playbook_path.write_text(
				"## Wave 2\n### F-016\nImpacted Requirement IDs:\n- `R-6.2-01`\n- `R-6.2-02`\n- `R-5.1-01`\n",
				encoding="utf-8",
			)
			handoff_path.write_text("# handoff\n", encoding="utf-8")
			sqlite_adapter.init_db(str(db_path))

			with patch.object(constants, "DEFAULT_RFC_PATH", str(rfc_path)), patch.object(
				constants, "DEFAULT_MATRIX_PATH", str(matrix_path)
			), patch.object(constants, "DEFAULT_PLAYBOOK_PATH", str(playbook_path)), patch.object(
				constants, "DEFAULT_HANDOFF_PATH", str(handoff_path)
			), patch.object(
				constants, "DEFAULT_DB_PATH", str(db_path)
			):
				actions = build_action_queue(_report({}))

		triage = [action for action in actions if action["type"] == "triage_section"]
		self.assertEqual(len(triage), 2)
		self.assertEqual(triage[0]["target"], "F-016:6.2")
		self.assertEqual(triage[1]["target"], "F-016:5.1")
		for action in triage:
			self.assertTrue(action["commands"])
			self.assertTrue(action["links"])

	def test_build_action_queue_uses_context_paths_and_db(self) -> None:
		with TemporaryDirectory() as tmpdir:
			root = Path(tmpdir)
			rfc_path = root / "rfc.md"
			matrix_path = root / "matrix.md"
			playbook_path = root / "playbook.md"
			handoff_path = root / "handoff.md"
			db_path = root / "state.db"

			rfc_path.write_text("## 6.2\nThis SHOULD be tracked.\n", encoding="utf-8")
			matrix_path.write_text(
				_matrix_text(
					[
						("R-6.2-01", "RFC 6.2:L2", "partial", "F-010"),
					]
				),
				encoding="utf-8",
			)
			playbook_path.write_text(
				"## Wave 2\n### F-010\nImpacted Requirement IDs:\n- `R-6.2-01`\n",
				encoding="utf-8",
			)
			handoff_path.write_text("# handoff\n", encoding="utf-8")

			sqlite_adapter.init_db(str(db_path))
			sqlite_adapter.upsert_finding_state(
				finding_id="F-010",
				status="ready_for_validation",
				note=None,
				db_path=str(db_path),
			)

			ctx = ValidatorContext(
				rfc_path=str(rfc_path),
				matrix_path=str(matrix_path),
				playbook_path=str(playbook_path),
				handoff_path=str(handoff_path),
				workspace_root=str(root),
				state_db_path=str(db_path),
			)

			with patch.object(constants, "DEFAULT_RFC_PATH", str(root / "missing-rfc.md")), patch.object(
				constants, "DEFAULT_MATRIX_PATH", str(root / "missing-matrix.md")
			), patch.object(constants, "DEFAULT_PLAYBOOK_PATH", str(root / "missing-playbook.md")), patch.object(
				constants, "DEFAULT_HANDOFF_PATH", str(root / "missing-handoff.md")
			), patch.object(
				constants, "DEFAULT_DB_PATH", str(root / "missing-state.db")
			):
				actions = build_action_queue(_report({}), ctx)

		self.assertTrue(any(action["tier"] == 2 and action["type"] == "run_validate" for action in actions))
