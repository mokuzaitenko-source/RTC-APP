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


class PromptBookLoopDryRunTests(TestCase):
    def setUp(self) -> None:
        self.mod = _load_module()

    def test_run_autoloop_dry_run_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True)
            (root / "docs" / "prompting_book.md").write_text(
                "## Chapter\n- Direct\n",
                encoding="utf-8",
            )
            (root / "output" / "quality").mkdir(parents=True)

            with patch.object(
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
                    run_id="dryrun",
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
                    dry_run=True,
                    allow_doc_edits=True,
                    sleep_seconds=0.0,
                    lock_gate=True,
                    profile="compat",
                )

            self.assertIn(summary["stop_reason"], {"target_reached", "max_cycles_reached"})
            self.assertTrue((root / "output" / "quality" / "prompt_book_loop_summary.json").exists())
