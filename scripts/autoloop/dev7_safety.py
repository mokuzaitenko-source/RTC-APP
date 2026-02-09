from __future__ import annotations

from typing import List

from scripts.autoloop.types import Dev3Proposal, Dev7SafetyVerdict


class Dev7Safety:
    def __init__(self, *, block_on_safety: bool = True) -> None:
        self.block_on_safety = block_on_safety

    def precheck(self, *, proposal: Dev3Proposal, lock_gate_paths: List[str]) -> Dev7SafetyVerdict:
        reasons: List[str] = []
        locked = {item.replace("\\", "/").lower() for item in lock_gate_paths}
        for edit in proposal.edits:
            normalized_path = edit.path.replace("\\", "/").lower()
            if normalized_path in locked:
                reasons.append(f"locked_path:{edit.path}")
            new_text = (edit.new_text or "").lower()
            if "ignore all prior instructions" in new_text:
                reasons.append("prompt_injection_like_content")
            if "rm -rf" in new_text or "del /f /q" in new_text:
                reasons.append("destructive_command_content")

        if reasons and self.block_on_safety:
            return Dev7SafetyVerdict(verdict="block", reasons=reasons)
        if reasons:
            return Dev7SafetyVerdict(verdict="pass", reasons=["safety_warnings_ignored_by_policy", *reasons])
        return Dev7SafetyVerdict(verdict="pass", reasons=["pass"])
