import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from scripts.autoloop.dev2_executor import Dev2ExecutionResult
from scripts.autoloop.types import Dev3Proposal, Dev4Review, Dev7SafetyVerdict, Dev8ReleaseVerdict, ProposalEdit


def _load_module():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "run_prompt_book_loop.py"
    spec = importlib.util.spec_from_file_location("run_prompt_book_loop", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _PatchHandle:
    def __init__(self) -> None:
        self.rolled = False

    def rollback(self) -> None:
        self.rolled = True


class AutoloopCollabReleaseBlockRollbackTests(TestCase):
    def setUp(self) -> None:
        self.mod = _load_module()

    def test_release_block_triggers_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True)
            (root / "docs" / "prompting_book.md").write_text("## Loop\n- Decompose\n", encoding="utf-8")
            (root / "output" / "quality").mkdir(parents=True)
            patch_handle = _PatchHandle()
            proposal = Dev3Proposal(
                proposal_id="p1",
                upgrade_id="U01",
                goal="Improve U01",
                rationale="x",
                edits=[ProposalEdit(path="tests/test_x.py", operation="append", new_text="#x\n")],
                expected_effect="x",
                risk_notes=[],
                sources=[{"source": "local", "ref": "docs/prompting_book.md"}],
            )
            with patch.object(self.mod.Dev3Strategist, "propose", return_value=proposal), patch.object(
                self.mod.Dev4Reviewer, "review", return_value=Dev4Review(verdict="approved", reasons=["ok"])
            ), patch.object(
                self.mod.Dev7Safety, "precheck", return_value=Dev7SafetyVerdict(verdict="pass", reasons=["ok"])
            ), patch.object(
                self.mod.Dev8Release, "verdict", return_value=Dev8ReleaseVerdict(verdict="block", reasons=["release"])
            ), patch.object(
                self.mod,
                "apply_and_maybe_rollback",
                return_value=Dev2ExecutionResult(applied=True, files_changed=["tests/test_x.py"], patch_handle=patch_handle),
            ), patch.object(
                self.mod,
                "run_quality_checks",
                return_value={"checks": [], "checks_pass": True},
            ), patch.object(
                self.mod,
                "run_airtight_gate",
                return_value={
                    "overall_x": 10.0,
                    "checks_pass": True,
                    "smoke_ratio": 1.0,
                    "stress_ratio": 1.0,
                    "gate_smoke_passed": True,
                    "gate_stress_passed": True,
                },
            ), patch.object(
                self.mod,
                "_run_internal_eval_subprocess",
                side_effect=[{"score_100": 100.0}, {"score_100": 100.0}, {"score_100": 100.0}, {"score_100": 100.0}],
            ):
                summary = self.mod.run_autoloop(
                    repo_root=root,
                    run_id="release-block",
                    prompt_book_path=root / "docs" / "prompting_book.md",
                    output_path=root / "output" / "quality" / "prompt_book_loop.jsonl",
                    summary_json_path=root / "output" / "quality" / "prompt_book_loop_summary.json",
                    summary_md_path=root / "output" / "quality" / "prompt_book_loop_summary.md",
                    iterations=1,
                    max_cycles=1,
                    max_minutes=5,
                    target_x=100.0,
                    model="gpt-4.1-mini",
                    autocommit=False,
                    dry_run=False,
                    allow_doc_edits=True,
                    sleep_seconds=0.0,
                    lock_gate=True,
                    profile="strict",
                    upgrade_target=1,
                )

            self.assertEqual(summary["release_blocks"], 1)
            self.assertTrue(patch_handle.rolled)
            records = (root / "output" / "quality" / "prompt_book_loop.jsonl").read_text(encoding="utf-8").splitlines()
            payload = json.loads(records[-1])
            self.assertTrue(payload["rollback_triggered"])
