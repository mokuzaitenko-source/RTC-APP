from __future__ import annotations

from typing import Any, Dict, List, Optional

from scripts.autoloop.types import UpgradeSpec


UPGRADE_IDS: List[str] = [
    "U01",
    "U02",
    "U03",
    "U04",
    "U05",
    "U06",
    "U07",
    "U08",
    "U09",
    "U10",
]


def get_upgrade_specs() -> List[UpgradeSpec]:
    return [
        UpgradeSpec(
            upgrade_id="U01",
            goal="build/debug intent precision",
            allowed_paths=["app/backend/services/", "tests/", "docs/"],
            forbidden_paths=["scripts/run_airtight_gate.py", "run_quality_gate.bat"],
            required_checks=["python_unittest", "python_pytest"],
            risk_class="low",
            default_prompt_book_technique="Task Decomposition",
            success_predicate="workflow_build_debug_precision",
        ),
        UpgradeSpec(
            upgrade_id="U02",
            goal="clarify over-trigger control",
            allowed_paths=["app/backend/services/", "tests/", "docs/"],
            forbidden_paths=["scripts/run_airtight_gate.py", "run_quality_gate.bat"],
            required_checks=["python_unittest", "python_pytest"],
            risk_class="low",
            default_prompt_book_technique="Constraint Prompting",
            success_predicate="workflow_clarify_control",
        ),
        UpgradeSpec(
            upgrade_id="U03",
            goal="strict 3+1+1 response consistency",
            allowed_paths=["app/backend/services/", "tests/", "docs/"],
            forbidden_paths=["scripts/run_airtight_gate.py", "run_quality_gate.bat"],
            required_checks=["python_unittest", "python_pytest"],
            risk_class="medium",
            default_prompt_book_technique="Output Formatting Contracts",
            success_predicate="workflow_strict_3_1_1",
        ),
        UpgradeSpec(
            upgrade_id="U04",
            goal="stream-end resilience",
            allowed_paths=["app/frontend/", "tests/", "app/backend/", "docs/"],
            forbidden_paths=["scripts/run_airtight_gate.py", "run_quality_gate.bat"],
            required_checks=["node_check_app_js", "python_pytest"],
            risk_class="medium",
            default_prompt_book_technique="Failure Mode Analysis",
            success_predicate="reliability_stream_end",
        ),
        UpgradeSpec(
            upgrade_id="U05",
            goal="usefulness feedback fidelity",
            allowed_paths=["scripts/", "tests/", "README.md", "docs/"],
            forbidden_paths=["scripts/run_airtight_gate.py", "run_quality_gate.bat"],
            required_checks=["python_pytest"],
            risk_class="low",
            default_prompt_book_technique="Self-Critique Loop",
            success_predicate="workflow_usefulness",
        ),
        UpgradeSpec(
            upgrade_id="U06",
            goal="refine-action quality and safety",
            allowed_paths=["app/backend/services/", "app/backend/aca/", "tests/", "docs/"],
            forbidden_paths=["scripts/run_airtight_gate.py", "run_quality_gate.bat"],
            required_checks=["python_unittest", "python_pytest"],
            risk_class="medium",
            default_prompt_book_technique="Refinement and Verification",
            success_predicate="workflow_refine_safety",
        ),
        UpgradeSpec(
            upgrade_id="U07",
            goal="help/settings UX clarity",
            allowed_paths=["app/frontend/", "tests/", "docs/"],
            forbidden_paths=["scripts/run_airtight_gate.py", "run_quality_gate.bat"],
            required_checks=["node_check_app_js", "python_pytest"],
            risk_class="low",
            default_prompt_book_technique="User-Centered Prompting",
            success_predicate="ux_help_settings_clarity",
        ),
        UpgradeSpec(
            upgrade_id="U08",
            goal="autoloop score realism hardening",
            allowed_paths=["scripts/", "tests/", "docs/"],
            forbidden_paths=["scripts/run_airtight_gate.py", "run_quality_gate.bat"],
            required_checks=["python_pytest"],
            risk_class="low",
            default_prompt_book_technique="Metric Grounding",
            success_predicate="score_realism",
        ),
        UpgradeSpec(
            upgrade_id="U09",
            goal="debug-pack depth expansion",
            allowed_paths=["scripts/", "tests/", "docs/"],
            forbidden_paths=["scripts/run_airtight_gate.py", "run_quality_gate.bat"],
            required_checks=["python_pytest"],
            risk_class="medium",
            default_prompt_book_technique="Scenario Expansion",
            success_predicate="debug_pack_depth",
        ),
        UpgradeSpec(
            upgrade_id="U10",
            goal="rollback/commit/release integrity",
            allowed_paths=["scripts/", "tests/", "docs/"],
            forbidden_paths=["scripts/run_airtight_gate.py", "run_quality_gate.bat"],
            required_checks=["python_unittest", "python_pytest"],
            risk_class="high",
            default_prompt_book_technique="Safety-First Control",
            success_predicate="release_integrity",
        ),
    ]


def get_next_upgrade(accepted_upgrade_ids: List[str]) -> Optional[UpgradeSpec]:
    accepted = set(accepted_upgrade_ids)
    for spec in get_upgrade_specs():
        if spec.upgrade_id not in accepted:
            return spec
    return None


def success_predicate_met(
    *,
    upgrade: UpgradeSpec,
    workflow_eval: Dict[str, Any],
    ux_eval: Dict[str, Any],
    gate_result: Dict[str, Any],
    checks_pass: bool,
) -> bool:
    workflow_score = float(workflow_eval.get("score_100", 0.0) or 0.0)
    ux_score = float(ux_eval.get("score_100", 0.0) or 0.0)
    overall_x = float(gate_result.get("overall_x", 0.0) or 0.0)
    smoke_ok = bool(gate_result.get("gate_smoke_passed", False))
    stress_ok = bool(gate_result.get("gate_stress_passed", False))
    gate_checks = bool(gate_result.get("checks_pass", False))

    if not checks_pass or not gate_checks:
        return False

    predicate = upgrade.success_predicate
    if predicate in {"workflow_build_debug_precision", "workflow_clarify_control", "workflow_strict_3_1_1", "workflow_usefulness", "workflow_refine_safety"}:
        return workflow_score >= 80.0 and smoke_ok and stress_ok
    if predicate in {"ux_help_settings_clarity"}:
        return ux_score >= 80.0 and smoke_ok
    if predicate in {"reliability_stream_end"}:
        return smoke_ok and stress_ok and overall_x >= 9.0
    if predicate in {"score_realism", "debug_pack_depth"}:
        return overall_x >= 9.0 and smoke_ok and stress_ok
    if predicate in {"release_integrity"}:
        return smoke_ok and stress_ok and overall_x >= 9.5
    return False
