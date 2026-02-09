import importlib.util
import os
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


class PromptBookLoopPolicyTests(TestCase):
    def setUp(self) -> None:
        self.mod = _load_module()

    def test_locked_paths_include_gate_and_self(self) -> None:
        self.assertTrue(self.mod.is_locked_path("scripts/run_prompt_book_loop.py", lock_gate=True))
        self.assertTrue(self.mod.is_locked_path("scripts/run_airtight_gate.py", lock_gate=True))
        self.assertFalse(self.mod.is_locked_path("README.md", lock_gate=True))

    def test_missing_openai_key_fails_fast(self) -> None:
        prev = os.environ.get("OPENAI_API_KEY")
        try:
            os.environ.pop("OPENAI_API_KEY", None)
            with self.assertRaises(RuntimeError):
                self.mod._require_openai_key(dry_run=False)
            with self.assertRaises(RuntimeError):
                self.mod.generate_improvement_proposal(
                    prompt="Current weakest dimension: workflow",
                    model="gpt-4.1-mini",
                    dry_run=False,
                )
        finally:
            if prev is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = prev

    def test_doc_edits_blocked_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                self.mod._validate_and_normalize_edits(
                    edits=[
                        {
                            "path": "docs/example.md",
                            "operation": "write",
                            "new_text": "x",
                        }
                    ],
                    repo_root=root,
                    allow_doc_edits=False,
                    lock_gate=True,
                )
