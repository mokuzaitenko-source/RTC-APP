from __future__ import annotations

from typing import List

from scripts.autoloop.types import Dev3Proposal, Dev4Review, UpgradeSpec


class Dev4Reviewer:
    def __init__(self, *, policy: str = "strict", research_policy: str = "primary_docs") -> None:
        self.policy = policy
        self.research_policy = research_policy

    @staticmethod
    def _path_allowed(path: str, allowed: List[str], forbidden: List[str]) -> bool:
        normalized = path.replace("\\", "/").lower()
        if any(normalized.startswith(prefix.lower()) for prefix in forbidden):
            return False
        if not allowed:
            return True
        return any(normalized.startswith(prefix.lower()) for prefix in allowed)

    def review(self, *, proposal: Dev3Proposal, upgrade: UpgradeSpec) -> Dev4Review:
        reasons: List[str] = []
        if self.research_policy != "local_only" and not proposal.sources:
            reasons.append("missing_provenance")

        for edit in proposal.edits:
            if not self._path_allowed(edit.path, upgrade.allowed_paths, upgrade.forbidden_paths):
                reasons.append(f"path_not_allowed:{edit.path}")

        if not proposal.goal.strip():
            reasons.append("missing_goal")

        if reasons:
            return Dev4Review(verdict="rejected", reasons=reasons)

        if self.policy == "strict" and not proposal.edits:
            return Dev4Review(verdict="revise", reasons=["no_edits_proposed"])

        return Dev4Review(verdict="approved", reasons=["approved"])
