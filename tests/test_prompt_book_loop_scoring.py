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


class PromptBookLoopScoringTests(TestCase):
    def setUp(self) -> None:
        self.mod = _load_module()

    def test_compute_scores_normalizes_gate_to_100(self) -> None:
        scores = self.mod.compute_scores(
            gate={
                "overall_x": 9.2,
                "checks_pass": True,
                "smoke_ratio": 1.0,
                "stress_ratio": 1.0,
                "gate_smoke_passed": True,
                "gate_stress_passed": True,
            },
            workflow_eval={"score_100": 80.0},
            ux_eval={"score_100": 90.0},
        )
        self.assertEqual(scores["x_gate_100"], 92.0)
        self.assertEqual(scores["reliability"], 100.0)
        self.assertEqual(scores["x_composite_100"], 88.0)

    def test_should_stop_requires_exact_target(self) -> None:
        stop = self.mod.should_stop(
            scores={"x_gate_100": 100.0, "x_composite_100": 100.0},
            checks_pass=True,
            target_x=100.0,
            cycle=1,
        )
        self.assertTrue(stop)

    def test_should_stop_false_if_checks_fail(self) -> None:
        stop = self.mod.should_stop(
            scores={"x_gate_100": 100.0, "x_composite_100": 100.0},
            checks_pass=False,
            target_x=100.0,
            cycle=1,
        )
        self.assertFalse(stop)

    def test_should_stop_false_without_progress(self) -> None:
        stop = self.mod.should_stop(
            scores={"x_gate_100": 100.0, "x_composite_100": 100.0},
            checks_pass=True,
            target_x=100.0,
            cycle=1,
            progress_made=False,
        )
        self.assertFalse(stop)
