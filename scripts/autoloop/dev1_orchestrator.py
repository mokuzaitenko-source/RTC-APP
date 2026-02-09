from __future__ import annotations

from dataclasses import dataclass
from typing import List

from scripts.autoloop.types import CycleDiagnostics, ProfileMode
from scripts.autoloop.upgrade_catalog import get_next_upgrade


@dataclass
class Dev1Orchestrator:
    profile: ProfileMode = "strict"
    upgrade_target: int = 10
    target_x: float = 100.0

    def state_label(self, *, cycle: int) -> str:
        return f"{self.profile}:cycle_{cycle}"

    def next_upgrade_id(self, *, accepted_upgrade_ids: List[str]) -> str:
        next_upgrade = get_next_upgrade(accepted_upgrade_ids)
        return next_upgrade.upgrade_id if next_upgrade is not None else "NONE"

    def should_stop(
        self,
        *,
        accepted_upgrades_total: int,
        x_composite_100: float,
        x_gate_100: float,
        checks_green: bool,
    ) -> bool:
        if self.profile == "compat":
            return checks_green and x_composite_100 == self.target_x and x_gate_100 == self.target_x
        return (
            checks_green
            and accepted_upgrades_total >= self.upgrade_target
            and x_composite_100 == self.target_x
            and x_gate_100 == self.target_x
        )

    def make_diagnostics(
        self,
        *,
        cycle: int,
        weakest_dimension: str,
        latest_scores: dict,
        accepted_upgrade_ids: List[str],
        prior_failures: int,
    ) -> CycleDiagnostics:
        return CycleDiagnostics(
            cycle=cycle,
            profile=self.profile,
            weakest_dimension=weakest_dimension,
            latest_scores=latest_scores,
            accepted_upgrades_total=len(accepted_upgrade_ids),
            accepted_upgrade_ids=accepted_upgrade_ids.copy(),
            prior_failures=prior_failures,
        )
