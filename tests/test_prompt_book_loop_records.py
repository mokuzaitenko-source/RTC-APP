import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest import TestCase


def _load_module():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "run_prompt_book_loop.py"
    spec = importlib.util.spec_from_file_location("run_prompt_book_loop", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PromptBookLoopRecordTests(TestCase):
    def setUp(self) -> None:
        self.mod = _load_module()

    def test_write_cycle_record_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "prompt_book_loop.jsonl"
            summary_json = Path(tmp) / "prompt_book_loop_summary.json"
            summary_md = Path(tmp) / "prompt_book_loop_summary.md"

            self.mod.write_cycle_record(
                output_path=output,
                record={
                    "run_id": "r1",
                    "cycle": 1,
                    "prompt_technique": "Direct",
                    "proposal_summary": "Improve tests",
                    "files_changed": ["README.md"],
                    "checks_pass": True,
                    "gate_smoke_passed": True,
                    "gate_stress_passed": True,
                    "x_gate_100": 100.0,
                    "x_composite_100": 95.0,
                    "improved": True,
                    "commit_hash": "abc",
                    "timestamp_utc": "2026-02-09T00:00:00Z",
                },
            )
            line = output.read_text(encoding="utf-8").strip()
            parsed = json.loads(line)
            self.assertEqual(parsed["cycle"], 1)

            self.mod.finalize_summary(
                summary_json_path=summary_json,
                summary_md_path=summary_md,
                payload={
                    "run_id": "r1",
                    "stop_reason": "target_reached",
                    "cycles_completed": 1,
                    "best_x_composite_100": 95.0,
                    "best_x_gate_100": 100.0,
                    "final_scores": {
                        "workflow": 95.0,
                        "reliability": 100.0,
                        "ux": 90.0,
                        "x_composite_100": 95.0,
                        "x_gate_100": 100.0,
                    },
                    "commit_hashes": ["abc"],
                },
            )
            self.assertTrue(summary_json.exists())
            self.assertTrue(summary_md.exists())
