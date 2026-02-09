from __future__ import annotations

from dataclasses import dataclass
from typing import List

from scripts.autoloop.types import Dev3Proposal


@dataclass
class Dev6UXVerdict:
    verdict: str
    reasons: List[str]


class Dev6UX:
    def review(self, *, proposal: Dev3Proposal, ux_score_100: float) -> Dev6UXVerdict:
        touched_frontend = any(edit.path.replace("\\", "/").startswith("app/frontend/") for edit in proposal.edits)
        if not touched_frontend:
            return Dev6UXVerdict(verdict="pass", reasons=["no_frontend_changes"])
        if ux_score_100 >= 80.0:
            return Dev6UXVerdict(verdict="pass", reasons=["ux_checks_healthy"])
        return Dev6UXVerdict(verdict="warn", reasons=["frontend_changed_low_ux_score"])
