from unittest import TestCase

from scripts.autoloop.dev5_eval import compute_v2_scores


class AutoloopDev5EvalTests(TestCase):
    def test_compute_v2_scores_weighted_composite(self) -> None:
        scores = compute_v2_scores(
            gate={
                "overall_x": 10.0,
                "checks_pass": True,
                "smoke_ratio": 1.0,
                "stress_ratio": 1.0,
                "gate_smoke_passed": True,
                "gate_stress_passed": True,
            },
            workflow_eval={"score_100": 80.0},
            ux_eval={"score_100": 90.0},
            previous_x_composite_100=70.0,
            release_score=100.0,
        )
        self.assertEqual(scores.x_gate_100, 100.0)
        self.assertEqual(scores.reliability, 100.0)
        self.assertGreater(scores.x_composite_100, 80.0)
        self.assertGreater(scores.score_delta, 0.0)
