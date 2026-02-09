from __future__ import annotations

from typing import Any, Dict

from scripts.autoloop.types import CycleScores


def _reliability_from_gate(gate: Dict[str, Any]) -> float:
    checks_score = 100.0 if bool(gate.get("checks_pass", False)) else 0.0
    smoke_score = round(float(gate.get("smoke_ratio", 0.0) or 0.0) * 100.0, 2)
    stress_score = round(float(gate.get("stress_ratio", 0.0) or 0.0) * 100.0, 2)
    return round((0.40 * checks_score) + (0.40 * smoke_score) + (0.20 * stress_score), 2)


def compute_v2_scores(
    *,
    gate: Dict[str, Any],
    workflow_eval: Dict[str, Any],
    ux_eval: Dict[str, Any],
    previous_x_composite_100: float,
    release_score: float,
) -> CycleScores:
    x_gate_100 = round(float(gate.get("overall_x", 0.0) or 0.0) * 10.0, 2)
    workflow = round(float(workflow_eval.get("score_100", 0.0) or 0.0), 2)
    reliability = _reliability_from_gate(gate)
    ux = round(float(ux_eval.get("score_100", 0.0) or 0.0), 2)
    safety = 100.0 if not bool(workflow_eval.get("safety_blocked", False)) else 0.0
    release = round(float(release_score), 2)

    x_composite_100 = round(
        (0.35 * workflow)
        + (0.25 * reliability)
        + (0.15 * ux)
        + (0.15 * safety)
        + (0.10 * release),
        2,
    )
    score_delta = round(x_composite_100 - float(previous_x_composite_100), 2)

    return CycleScores(
        workflow=workflow,
        reliability=reliability,
        ux=ux,
        safety=safety,
        release=release,
        x_gate_100=x_gate_100,
        x_composite_100=x_composite_100,
        score_delta=score_delta,
        gate_smoke_passed=bool(gate.get("gate_smoke_passed", False)),
        gate_stress_passed=bool(gate.get("gate_stress_passed", False)),
        gate_checks_pass=bool(gate.get("checks_pass", False)),
    )
