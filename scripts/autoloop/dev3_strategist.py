from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional

from scripts.autoloop.research_pack import resolve_research_sources
from scripts.autoloop.types import Dev3Proposal, ProposalEdit, UpgradeSpec


ProposalGenerator = Callable[[str, str, bool], Dict[str, Any]]


class Dev3Strategist:
    def __init__(self, *, mode: str = "local", research_policy: str = "primary_docs") -> None:
        self.mode = mode
        self.research_policy = research_policy

    def build_prompt(
        self,
        *,
        cycle: int,
        technique: str,
        weakest_dimension: str,
        latest_scores: Dict[str, float],
        upgrade: UpgradeSpec,
    ) -> str:
        return (
            "You are Dev3 (Strategist/Researcher) for RTC-APP autoloop.\n"
            f"Cycle: {cycle}\n"
            f"Upgrade target: {upgrade.upgrade_id} - {upgrade.goal}\n"
            f"Technique: {technique}\n"
            f"Weakest dimension: {weakest_dimension}\n"
            f"Scores: workflow={latest_scores.get('workflow', 0.0):.2f}, "
            f"reliability={latest_scores.get('reliability', 0.0):.2f}, "
            f"ux={latest_scores.get('ux', 0.0):.2f}\n"
            "Return strict JSON: goal, rationale, edits, expected_effect, risk_notes."
        )

    def _local_proposal(self, *, upgrade: UpgradeSpec, prompt: str) -> Dev3Proposal:
        sources = resolve_research_sources(self.research_policy)[:3]
        log_line = f"- {upgrade.upgrade_id}: local-first deterministic proposal generated.\n"
        return Dev3Proposal(
            proposal_id=f"dev3-{upgrade.upgrade_id}-{uuid.uuid4().hex[:8]}",
            upgrade_id=upgrade.upgrade_id,
            goal=f"[LOCAL] {upgrade.goal}",
            rationale="Local-first deterministic proposal. Uses catalog + prompt book; safe no-op when no deterministic patch is available.",
            edits=[
                ProposalEdit(
                    path="docs/autoloop_upgrade_log.md",
                    operation="append",
                    new_text=log_line,
                )
            ],
            expected_effect=f"Incrementally improve {upgrade.upgrade_id} while preserving contracts.",
            risk_notes=["local_first_mode", "no_api_required"],
            sources=sources,
        )

    def _from_payload(self, *, payload: Dict[str, Any], upgrade: UpgradeSpec) -> Dev3Proposal:
        edit_models: List[ProposalEdit] = []
        for raw in payload.get("edits", []):
            edit_models.append(
                ProposalEdit(
                    path=str(raw.get("path", "")),
                    operation=str(raw.get("operation", "replace")),  # validated later by runner
                    old_text=raw.get("old_text"),
                    new_text=raw.get("new_text"),
                )
            )

        return Dev3Proposal(
            proposal_id=f"dev3-{upgrade.upgrade_id}-{uuid.uuid4().hex[:8]}",
            upgrade_id=upgrade.upgrade_id,
            goal=str(payload.get("goal", upgrade.goal)),
            rationale=str(payload.get("rationale", "")),
            edits=edit_models,
            expected_effect=str(payload.get("expected_effect", "")),
            risk_notes=list(payload.get("risk_notes", [])) if isinstance(payload.get("risk_notes"), list) else [str(payload.get("risk_notes", ""))],
            sources=resolve_research_sources(self.research_policy),
        )

    def propose(
        self,
        *,
        cycle: int,
        technique: str,
        weakest_dimension: str,
        latest_scores: Dict[str, float],
        upgrade: UpgradeSpec,
        model: str,
        dry_run: bool,
        proposal_generator: Optional[ProposalGenerator] = None,
    ) -> Dev3Proposal:
        prompt = self.build_prompt(
            cycle=cycle,
            technique=technique,
            weakest_dimension=weakest_dimension,
            latest_scores=latest_scores,
            upgrade=upgrade,
        )
        if self.mode == "local":
            return self._local_proposal(upgrade=upgrade, prompt=prompt)

        if self.mode in {"cloud", "hybrid"} and proposal_generator is not None:
            try:
                payload = proposal_generator(prompt, model, dry_run)
                return self._from_payload(payload=payload, upgrade=upgrade)
            except Exception:
                if self.mode == "cloud":
                    raise
                return self._local_proposal(upgrade=upgrade, prompt=prompt)

        return self._local_proposal(upgrade=upgrade, prompt=prompt)

    @staticmethod
    def as_payload(proposal: Dev3Proposal) -> Dict[str, Any]:
        payload = asdict(proposal)
        payload["edits"] = [asdict(edit) for edit in proposal.edits]
        return payload
