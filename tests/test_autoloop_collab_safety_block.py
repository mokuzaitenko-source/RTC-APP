import importlib.util
import sys
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from scripts.autoloop.types import Dev3Proposal, Dev4Review, Dev7SafetyVerdict, ProposalEdit


def _load_module():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "run_prompt_book_loop.py"
    spec = importlib.util.spec_from_file_location("run_prompt_book_loop", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AutoloopCollabSafetyBlockTests(TestCase):
    def setUp(self) -> None:
        self.mod = _load_module()

    def test_safety_block_increments_counter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True)
            (root / "docs" / "prompting_book.md").write_text("## Loop\n- Decompose\n", encoding="utf-8")
            (root / "output" / "quality").mkdir(parents=True)
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
                self.mod.Dev7Safety, "precheck", return_value=Dev7SafetyVerdict(verdict="block", reasons=["unsafe"])
            ):
                summary = self.mod.run_autoloop(
                    repo_root=root,
                    run_id="safety",
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
            self.assertEqual(summary["safety_blocks"], 1)
            self.assertEqual(summary["accepted_upgrades_total"], 0)
