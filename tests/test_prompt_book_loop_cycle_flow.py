import importlib.util
import sys
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch


def _load_module():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "run_prompt_book_loop.py"
    spec = importlib.util.spec_from_file_location("run_prompt_book_loop", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _FakePatch:
    def __init__(self) -> None:
        self.changed_files = ["README.md"]
        self.rolled_back = False

    def rollback(self) -> None:
        self.rolled_back = True


class PromptBookLoopCycleFlowTests(TestCase):
    def setUp(self) -> None:
        self.mod = _load_module()

    def _setup_root(self) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "prompting_book.md").write_text("## Chapter\n- Direct\n", encoding="utf-8")
        (root / "output" / "quality").mkdir(parents=True)
        return root

    def test_successful_cycle_commits_when_improved(self) -> None:
        root = self._setup_root()
        fake_patch = _FakePatch()
        with patch.object(
            self.mod,
            "generate_improvement_proposal",
            return_value={
                "goal": "Improve",
                "rationale": "x",
                "edits": [{"path": "README.md", "operation": "append", "new_text": "x"}],
                "expected_effect": "x",
                "risk_notes": [],
            },
        ), patch.object(
            self.mod,
            "_validate_and_normalize_edits",
            return_value=[{"path": "README.md", "operation": "append", "new_text": "x"}],
        ), patch.object(
            self.mod,
            "apply_proposal",
            return_value=fake_patch,
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
            side_effect=[{"score_100": 90.0}, {"score_100": 90.0}, {"score_100": 100.0}, {"score_100": 100.0}],
        ), patch.object(
            self.mod,
            "_require_openai_key",
            return_value="test-key",
        ), patch.object(
            self.mod,
            "commit_if_improved",
            return_value="abc123",
        ) as commit_mock:
            self.mod.run_autoloop(
                repo_root=root,
                run_id="flow-success",
                prompt_book_path=root / "docs" / "prompting_book.md",
                output_path=root / "output" / "quality" / "prompt_book_loop.jsonl",
                summary_json_path=root / "output" / "quality" / "prompt_book_loop_summary.json",
                summary_md_path=root / "output" / "quality" / "prompt_book_loop_summary.md",
                iterations=1,
                max_cycles=1,
                max_minutes=5,
                target_x=100.0,
                model="gpt-4.1-mini",
                autocommit=True,
                dry_run=False,
                allow_doc_edits=True,
                sleep_seconds=0.0,
                lock_gate=True,
                profile="compat",
            )
            self.assertEqual(commit_mock.call_count, 1)

    def test_failed_cycle_rolls_back_patch(self) -> None:
        root = self._setup_root()
        fake_patch = _FakePatch()
        with patch.object(
            self.mod,
            "generate_improvement_proposal",
            return_value={
                "goal": "Break",
                "rationale": "x",
                "edits": [{"path": "README.md", "operation": "append", "new_text": "x"}],
                "expected_effect": "x",
                "risk_notes": [],
            },
        ), patch.object(
            self.mod,
            "_validate_and_normalize_edits",
            return_value=[{"path": "README.md", "operation": "append", "new_text": "x"}],
        ), patch.object(
            self.mod,
            "apply_proposal",
            return_value=fake_patch,
        ), patch.object(
            self.mod,
            "run_quality_checks",
            return_value={"checks": [], "checks_pass": False},
        ), patch.object(
            self.mod,
            "run_airtight_gate",
            return_value={
                "overall_x": 0.0,
                "checks_pass": False,
                "smoke_ratio": 0.0,
                "stress_ratio": 0.0,
                "gate_smoke_passed": False,
                "gate_stress_passed": False,
            },
        ), patch.object(
            self.mod,
            "_run_internal_eval_subprocess",
            side_effect=[{"score_100": 50.0}, {"score_100": 50.0}, {"score_100": 40.0}, {"score_100": 40.0}],
        ), patch.object(
            self.mod,
            "_require_openai_key",
            return_value="test-key",
        ):
            self.mod.run_autoloop(
                repo_root=root,
                run_id="flow-fail",
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
                profile="compat",
            )

        self.assertTrue(fake_patch.rolled_back)
