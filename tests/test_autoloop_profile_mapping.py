import importlib.util
import sys
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


class AutoloopProfileMappingTests(TestCase):
    def setUp(self) -> None:
        self.mod = _load_module()

    def test_dev_stack_v2_maps_to_strict_profile(self) -> None:
        captured = {}

        def _fake_run_autoloop(**kwargs):
            captured.update(kwargs)
            return {
                "run_id": "x",
                "stop_reason": "max_cycles_reached",
                "best_x_composite_100": 0.0,
                "best_x_gate_100": 0.0,
                "accepted_upgrades_total": 0,
                "profile": kwargs.get("profile", ""),
            }

        argv = [
            "run_prompt_book_loop.py",
            "--in-worktree-run",
            "--dev-stack-v2",
            "--profile",
            "compat",
            "--dry-run",
            "--max-cycles",
            "1",
            "--iterations",
            "1",
        ]
        with patch.object(sys, "argv", argv), patch.object(self.mod, "run_autoloop", side_effect=_fake_run_autoloop):
            rc = self.mod.main()
        self.assertEqual(rc, 0)
        self.assertEqual(captured.get("profile"), "strict")
        self.assertIn("dev-stack-v2", captured.get("deprecated_flags_used", []))
