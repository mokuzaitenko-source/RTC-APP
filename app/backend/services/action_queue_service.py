from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from app.backend import constants
from app.backend.adapters import sqlite_adapter
from app.backend.validators.matrix_parser import parse_core_rows
from app.backend.validators.playbook_parser import parse_findings
from app.backend.validators.rfc_normative import extract_normative_lines
from app.backend.validators.types import FindingInfo, RequirementRow, ValidatorContext, ValidatorReport


_READY_FOR_VALIDATION = "ready_for_validation"
_SECTION_RE = re.compile(r"^RFC\s+([0-9]+(?:\.[0-9]+)*)\s*:L\d+$", re.IGNORECASE)
_SEVERITY_SCORE = {"MUST": 3, "SHALL": 3, "SHOULD": 2, "MAY": 1}

_REPAIR_ACTIONS = {
    "toolchain_ok": {
        "command": "python scripts/sync_oversight_trace.py --rfc docs/oversight_assistant_rfc.md --matrix docs/requirements_trace_matrix.md --playbook docs/patch_playbook.md --handoff SESSION_HANDOFF.md",
        "link": "docs/specs/oversight_ops_app_v1_layer2_validators.md",
        "step": "Run sync, then rerun validate to clear toolchain failures.",
    },
    "parity": {
        "command": "python scripts/sync_oversight_trace.py --rfc docs/oversight_assistant_rfc.md --matrix docs/requirements_trace_matrix.md --playbook docs/patch_playbook.md --handoff SESSION_HANDOFF.md",
        "link": "docs/requirements_trace_matrix.md",
        "step": "Regenerate matrix rows and confirm parity with RFC normative lines.",
    },
    "no_orphan_must": {
        "command": "python scripts/sync_oversight_trace.py --rfc docs/oversight_assistant_rfc.md --matrix docs/requirements_trace_matrix.md --playbook docs/patch_playbook.md --handoff SESSION_HANDOFF.md",
        "link": "docs/oversight_assistant_rfc.md",
        "step": "Map orphan MUST/SHALL lines to core requirements and rerun validation.",
    },
    "finding_integrity": {
        "command": "python scripts/sync_oversight_trace.py --rfc docs/oversight_assistant_rfc.md --matrix docs/requirements_trace_matrix.md --playbook docs/patch_playbook.md --handoff SESSION_HANDOFF.md",
        "link": "docs/patch_playbook.md",
        "step": "Link every gap/partial requirement to at least one finding.",
    },
    "backlink_consistency": {
        "command": "python scripts/sync_oversight_trace.py --rfc docs/oversight_assistant_rfc.md --matrix docs/requirements_trace_matrix.md --playbook docs/patch_playbook.md --handoff SESSION_HANDOFF.md",
        "link": "docs/patch_playbook.md",
        "step": "Fix playbook impacted IDs to exactly match matrix backlinks.",
    },
    "blocker_pin": {
        "command": "python -m unittest tests/test_validator_fixtures.py",
        "link": "SESSION_HANDOFF.md",
        "step": "Restore Wave-1 blocker pinning and validate blocker coverage.",
    },
    "state_integrity": {
        "command": "python -m unittest tests/test_validator_fixtures.py",
        "link": "app/backend/adapters/sqlite_adapter.py",
        "step": "Repair invalid finding states and unknown finding IDs in SQLite state.",
    },
}


def _action_id(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return f"act_{digest[:12]}"


def _build_action(
    tier: int,
    action_type: str,
    target: str,
    title: str,
    why_now: str,
    steps: List[str],
    commands: List[str],
    links: List[str],
) -> Dict[str, object]:
    seed = f"{tier}:{action_type}:{target}:{title}"
    return {
        "action_id": _action_id(seed),
        "tier": tier,
        "type": action_type,
        "target": target,
        "title": title,
        "why_now": why_now,
        "steps": steps,
        "commands": commands,
        "links": links,
    }


def _load_state_status(db_path: str) -> Dict[str, str]:
    return {
        row["finding_id"]: row["status"]
        for row in sqlite_adapter.list_finding_states(db_path=db_path)
    }


def _resolve_runtime_paths(ctx: Optional[ValidatorContext]) -> Tuple[str, str, str, str]:
    if ctx is None:
        return (
            constants.DEFAULT_PLAYBOOK_PATH,
            constants.DEFAULT_MATRIX_PATH,
            constants.DEFAULT_RFC_PATH,
            constants.DEFAULT_DB_PATH,
        )
    return (
        ctx.playbook_path,
        ctx.matrix_path,
        ctx.rfc_path,
        ctx.state_db_path or constants.DEFAULT_DB_PATH,
    )


def _group_rows_by_finding(rows: Sequence[RequirementRow]) -> Dict[str, List[RequirementRow]]:
    grouped: Dict[str, List[RequirementRow]] = defaultdict(list)
    for row in rows:
        for finding_id in row.findings:
            grouped[finding_id].append(row)
    return grouped


def _impact_count(finding: FindingInfo, finding_rows: Mapping[str, Sequence[RequirementRow]]) -> int:
    req_ids = set(finding.impacted_req_ids)
    for row in finding_rows.get(finding.finding_id, []):
        req_ids.add(row.req_id)
    return len(req_ids)


def _severity_rank(
    finding: FindingInfo,
    finding_rows: Mapping[str, Sequence[RequirementRow]],
    normative_by_source: Mapping[str, str],
) -> int:
    max_rank = 0
    for row in finding_rows.get(finding.finding_id, []):
        rank = _SEVERITY_SCORE.get(normative_by_source.get(row.source_ref, ""), 0)
        max_rank = max(max_rank, rank)
    return max_rank


def _dependency_unblock_count(
    target_id: str,
    findings_by_id: Mapping[str, FindingInfo],
    status_by_finding: Mapping[str, str],
) -> int:
    count = 0
    for finding in findings_by_id.values():
        if target_id not in finding.dependencies:
            continue
        remaining = [dep for dep in finding.dependencies if dep != target_id]
        if all(status_by_finding.get(dep, "unstarted") == _READY_FOR_VALIDATION for dep in remaining):
            count += 1
    return count


def _finding_priority_key(
    finding: FindingInfo,
    findings_by_id: Mapping[str, FindingInfo],
    status_by_finding: Mapping[str, str],
    finding_rows: Mapping[str, Sequence[RequirementRow]],
    normative_by_source: Mapping[str, str],
) -> Tuple[int, int, int, str]:
    dependency_unblock = _dependency_unblock_count(
        finding.finding_id,
        findings_by_id,
        status_by_finding,
    )
    impact = _impact_count(finding, finding_rows)
    severity = _severity_rank(finding, finding_rows, normative_by_source)
    return (-dependency_unblock, -impact, -severity, finding.finding_id)


def _extract_section(source_ref: str) -> str:
    match = _SECTION_RE.match(source_ref.strip())
    if not match:
        return "unknown"
    return match.group(1)


def _finding_card(
    *,
    tier: int,
    finding: FindingInfo,
    status: str,
    finding_rows: Mapping[str, Sequence[RequirementRow]],
    dependency_unblock: int,
    impact_count: int,
    is_blocker: bool,
) -> Dict[str, object]:
    dep_hint = ", ".join(sorted(finding.dependencies)) if finding.dependencies else "none"
    impacted_list = sorted(set(finding.impacted_req_ids))
    impacted_hint = ", ".join(impacted_list[:5]) if impacted_list else "none listed"
    title_prefix = "Resolve Wave-1 blocker" if is_blocker else "Resolve finding"
    why_now = (
        f"{finding.finding_id} is {status}; impacts {impact_count} requirements, "
        f"unblocks {dependency_unblock} dependent findings."
    )
    links = [
        "docs/patch_playbook.md",
        "docs/requirements_trace_matrix.md",
        "SESSION_HANDOFF.md",
    ]
    if finding_rows.get(finding.finding_id):
        links = [
            "docs/patch_playbook.md",
            "docs/requirements_trace_matrix.md",
            "docs/oversight_assistant_rfc.md",
        ]
    return _build_action(
        tier=tier,
        action_type="resolve_blocker",
        target=finding.finding_id,
        title=f"{title_prefix} {finding.finding_id}",
        why_now=why_now,
        steps=[
            f"Review {finding.finding_id} dependencies ({dep_hint}) and impacted IDs ({impacted_hint}).",
            "Implement fixes and move finding state to ready_for_validation when complete.",
            "Run validate and confirm blocker/invariant status is resolved.",
        ],
        commands=[
            "python -m unittest tests/test_validator_fixtures.py",
            f"rg \"{finding.finding_id}\" docs/patch_playbook.md docs/requirements_trace_matrix.md",
        ],
        links=links,
    )


def _repair_card(invariant_id: str, message: str) -> Dict[str, object]:
    action = _REPAIR_ACTIONS.get(invariant_id, {})
    return _build_action(
        tier=3,
        action_type="repair_invariant",
        target=invariant_id,
        title=f"Repair invariant: {invariant_id}",
        why_now=message,
        steps=[action.get("step", "Review evidence and repair canonical docs, then rerun validate.")],
        commands=[action.get("command", "python -m unittest tests/test_validator_fixtures.py")],
        links=[action.get("link", "docs/specs/oversight_ops_app_v1_layer2_validators.md")],
    )


def _tier0_actions() -> List[Dict[str, object]]:
    return [
        _build_action(
            0,
            "run_sync",
            "sync",
            "Run sync to refresh trace",
            "Toolchain checks failed; sync must succeed before validation.",
            ["Run sync and review output."],
            [
                "python scripts/sync_oversight_trace.py --rfc docs/oversight_assistant_rfc.md --matrix docs/requirements_trace_matrix.md --playbook docs/patch_playbook.md --handoff SESSION_HANDOFF.md"
            ],
            ["docs/requirements_trace_matrix.md"],
        ),
        _build_action(
            0,
            "run_validate",
            "validate",
            "Run validators",
            "Toolchain checks failed; rerun validation after sync.",
            ["Run validator engine and review invariant evidence."],
            ["python -m unittest tests/test_validator_fixtures.py"],
            ["docs/specs/oversight_ops_app_v1_layer2_validators.md"],
        ),
    ]


def build_action_queue(
    report: ValidatorReport,
    ctx: Optional[ValidatorContext] = None,
) -> List[Dict[str, object]]:
    toolchain = next((inv for inv in report.invariants if inv.id == "toolchain_ok"), None)
    if toolchain and toolchain.status == "fail":
        return _tier0_actions()

    playbook_path, matrix_path, rfc_path, state_db_path = _resolve_runtime_paths(ctx)
    findings = parse_findings(playbook_path)
    rows = parse_core_rows(matrix_path)
    rfc_lines = extract_normative_lines(rfc_path)
    findings_by_id = {finding.finding_id: finding for finding in findings}
    status_by_finding = _load_state_status(state_db_path)
    finding_rows = _group_rows_by_finding(rows)
    normative_by_source = {line.rfc_line_id: line.normative_level for line in rfc_lines}
    actions: List[Dict[str, object]] = []

    # Tier 1: unresolved Wave-1 blockers.
    wave1_candidates = [
        findings_by_id[finding_id]
        for finding_id in constants.WAVE1_BLOCKERS
        if finding_id in findings_by_id
        and status_by_finding.get(finding_id, "unstarted") != _READY_FOR_VALIDATION
    ]
    wave1_candidates.sort(
        key=lambda item: _finding_priority_key(
            item,
            findings_by_id,
            status_by_finding,
            finding_rows,
            normative_by_source,
        )
    )
    for finding in wave1_candidates:
        actions.append(
            _finding_card(
                tier=1,
                finding=finding,
                status=status_by_finding.get(finding.finding_id, "unstarted"),
                finding_rows=finding_rows,
                dependency_unblock=_dependency_unblock_count(
                    finding.finding_id,
                    findings_by_id,
                    status_by_finding,
                ),
                impact_count=_impact_count(finding, finding_rows),
                is_blocker=True,
            )
        )

    # Tier 2: ready-for-validation gate.
    ready_findings = sorted(
        finding_id
        for finding_id, status in status_by_finding.items()
        if status == _READY_FOR_VALIDATION
    )
    if ready_findings:
        actions.append(
            _build_action(
                2,
                "run_validate",
                "validate",
                "Run validate for ready findings",
                f"{len(ready_findings)} findings are ready_for_validation; run invariants before new work.",
                [
                    "Run validation to confirm ready findings clear blocker/invariant checks.",
                    f"Ready IDs: {', '.join(ready_findings[:10])}",
                ],
                ["python -m unittest tests/test_validator_fixtures.py"],
                ["docs/specs/oversight_ops_app_v1_layer2_validators.md"],
            )
        )

    # Tier 3: invariant repair.
    for inv in report.invariants:
        if inv.status == "fail":
            actions.append(_repair_card(inv.id, inv.message))

    # Tier 4: non-blocker findings by impact.
    non_blockers = [
        finding
        for finding in findings
        if finding.finding_id not in constants.WAVE1_BLOCKERS
        and finding.finding_id != "F-016"
        and status_by_finding.get(finding.finding_id, "unstarted") != _READY_FOR_VALIDATION
    ]
    non_blockers.sort(
        key=lambda item: _finding_priority_key(
            item,
            findings_by_id,
            status_by_finding,
            finding_rows,
            normative_by_source,
        )
    )
    for finding in non_blockers:
        actions.append(
            _finding_card(
                tier=4,
                finding=finding,
                status=status_by_finding.get(finding.finding_id, "unstarted"),
                finding_rows=finding_rows,
                dependency_unblock=_dependency_unblock_count(
                    finding.finding_id,
                    findings_by_id,
                    status_by_finding,
                ),
                impact_count=_impact_count(finding, finding_rows),
                is_blocker=False,
            )
        )

    # Tier 5: section-scoped F-016 triage batches.
    triage_counts: Dict[str, int] = defaultdict(int)
    for row in rows:
        if row.status not in {"gap", "partial"}:
            continue
        if "F-016" not in row.findings:
            continue
        triage_counts[_extract_section(row.source_ref)] += 1
    for section, count in sorted(triage_counts.items(), key=lambda item: (-item[1], item[0])):
        actions.append(
            _build_action(
                5,
                "triage_section",
                f"F-016:{section}",
                f"Triage F-016 in section {section}",
                f"Section {section} has {count} F-016 gap/partial rows requiring triage.",
                [
                    "Review all F-016 rows for the section and group by shared root cause.",
                    "Create concrete patches and move affected findings to in_progress.",
                ],
                [
                    "rg \"F-016\" docs/requirements_trace_matrix.md",
                    "python -m unittest tests/test_validator_fixtures.py",
                ],
                [
                    "docs/requirements_trace_matrix.md",
                    "docs/patch_playbook.md",
                ],
            )
        )

    if not actions:
        actions.append(
            _build_action(
                5,
                "export_status",
                "status",
                "Export status snapshot",
                "All invariants passed and no pending work is ranked ahead of export.",
                ["Export a shareable status summary for handoff."],
                [
                    "python -c \"from app.backend.services.session_service import export_status; print(export_status())\""
                ],
                ["SESSION_HANDOFF.md"],
            )
        )

    return actions
