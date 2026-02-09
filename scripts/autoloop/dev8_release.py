from __future__ import annotations

from typing import List

from scripts.autoloop.types import Dev8ReleaseVerdict


class Dev8Release:
    def __init__(self, *, require_release_pass: bool = True) -> None:
        self.require_release_pass = require_release_pass

    def verdict(
        self,
        *,
        checks_green: bool,
        gate_smoke_passed: bool,
        gate_stress_passed: bool,
        ux_verdict: str,
    ) -> Dev8ReleaseVerdict:
        reasons: List[str] = []
        if not checks_green:
            reasons.append("checks_not_green")
        if not gate_smoke_passed:
            reasons.append("smoke_failed")
        if not gate_stress_passed:
            reasons.append("stress_failed")
        if ux_verdict == "warn":
            reasons.append("ux_warn")

        if reasons and self.require_release_pass:
            return Dev8ReleaseVerdict(verdict="block", reasons=reasons)
        if reasons:
            return Dev8ReleaseVerdict(verdict="pass", reasons=["release_warnings_ignored_by_policy", *reasons])
        return Dev8ReleaseVerdict(verdict="pass", reasons=["pass"])
