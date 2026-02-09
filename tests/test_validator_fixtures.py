import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from app.backend.adapters import sqlite_adapter
from app.backend.validators.engine import run_all_validators
from app.backend.validators.types import RunRecords, ValidatorContext

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_ROOT = ROOT / "tests" / "fixtures" / "validators"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_context(fixture_id: str, state_db_path: str) -> ValidatorContext:
    base = FIXTURES_ROOT / fixture_id
    state_seed = _load_json(base / "state_seed.json")
    records = state_seed.get("run_records", {})
    run_records = RunRecords(
        sync_exit_code=records.get("sync_exit_code"),
        validate_exit_code=records.get("validate_exit_code"),
    )
    sqlite_adapter.init_db(state_db_path)
    for row in state_seed.get("finding_states", []):
        sqlite_adapter.upsert_finding_state(
            finding_id=row.get("finding_id", ""),
            status=row.get("status", "unstarted"),
            note=row.get("note"),
            db_path=state_db_path,
        )
    return ValidatorContext(
        rfc_path=(base / "rfc.md").as_posix(),
        matrix_path=(base / "matrix.md").as_posix(),
        playbook_path=(base / "playbook.md").as_posix(),
        handoff_path=(base / "handoff.md").as_posix(),
        run_records=run_records,
        workspace_root=ROOT.as_posix(),
        state_db_path=state_db_path,
    )


def _serialize_report(report) -> dict:
    return {
        "run_id": "<RUN_ID>",
        "run_type": report.run_type,
        "status": report.status,
        "started_at": "<TS>",
        "ended_at": "<TS>",
        "invariants": [
            {
                "id": inv.id,
                "status": inv.status,
                "message": inv.message,
                "evidence": [
                    {
                        "kind": ev.kind,
                        "ref": ev.ref,
                        "detail": ev.detail,
                        "hash": ev.hash,
                    }
                    for ev in inv.evidence
                ],
                "recommended_action": inv.recommended_action,
                "suggested_matches": inv.suggested_matches or [],
            }
            for inv in report.invariants
        ],
        "summary": report.summary,
    }


def _run_fixture(fixture_id: str) -> dict:
    with TemporaryDirectory() as tmpdir:
        state_db_path = (Path(tmpdir) / "state.db").as_posix()
        ctx = _build_context(fixture_id, state_db_path)
        report = run_all_validators(ctx)
        return {
            "ok": True,
            "generated_at": "<TS>",
            "report": _serialize_report(report),
        }


class ValidatorFixtureTests(TestCase):
    def _assert_fixture(self, fixture_id: str) -> None:
        expected = _load_json(
            FIXTURES_ROOT / fixture_id / "expected.run_validate.json"
        )
        actual = _run_fixture(fixture_id)
        self.assertEqual(expected, actual)

    def test_v00_all_pass_source_line(self) -> None:
        self._assert_fixture("v00_all_pass_source_line")

    def test_v01_toolchain_fail_sync(self) -> None:
        self._assert_fixture("v01_toolchain_fail_sync")

    def test_v02_parity_off_by_one(self) -> None:
        self._assert_fixture("v02_parity_off_by_one")

    def test_v03_orphan_must_source_line(self) -> None:
        self._assert_fixture("v03_orphan_must_source_line")

    def test_v04_finding_integrity_gap_without_finding(self) -> None:
        self._assert_fixture("v04_finding_integrity_gap_without_finding")

    def test_v05_backlink_set_diff(self) -> None:
        self._assert_fixture("v05_backlink_set_diff")

    def test_v06_blocker_pin_missing_blocker(self) -> None:
        self._assert_fixture("v06_blocker_pin_missing_blocker")

    def test_v07_state_integrity_unknown_finding(self) -> None:
        self._assert_fixture("v07_state_integrity_unknown_finding")

    def test_v08_state_integrity_invalid_status(self) -> None:
        self._assert_fixture("v08_state_integrity_invalid_status")
