import importlib.util
import sys
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


class AutoloopTargetLogicTests(TestCase):
    def setUp(self) -> None:
        self.mod = _load_module()

    def test_strict_requires_upgrade_target(self) -> None:
        stop = self.mod.should_stop(
            scores={"x_gate_100": 100.0, "x_composite_100": 100.0},
            checks_pass=True,
            target_x=100.0,
            cycle=1,
            profile="strict",
            accepted_upgrades_total=9,
            upgrade_target=10,
        )
        self.assertFalse(stop)

    def test_compat_stops_on_score(self) -> None:
        stop = self.mod.should_stop(
            scores={"x_gate_100": 100.0, "x_composite_100": 100.0},
            checks_pass=True,
            target_x=100.0,
            cycle=1,
            profile="compat",
            accepted_upgrades_total=0,
            upgrade_target=10,
        )
        self.assertTrue(stop)
