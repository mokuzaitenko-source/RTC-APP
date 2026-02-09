from unittest import TestCase

from scripts.autoloop.dev7_safety import Dev7Safety
from scripts.autoloop.types import Dev3Proposal, ProposalEdit


class AutoloopDev7SafetyTests(TestCase):
    def test_locked_path_blocks(self) -> None:
        dev7 = Dev7Safety(block_on_safety=True)
        proposal = Dev3Proposal(
            proposal_id="p",
            upgrade_id="U10",
            goal="x",
            rationale="x",
            edits=[ProposalEdit(path="scripts/run_airtight_gate.py", operation="append", new_text="#x")],
            expected_effect="x",
            risk_notes=[],
            sources=[],
        )
        verdict = dev7.precheck(proposal=proposal, lock_gate_paths=["scripts/run_airtight_gate.py"])
        self.assertEqual(verdict.verdict, "block")

    def test_safe_proposal_passes(self) -> None:
        dev7 = Dev7Safety(block_on_safety=True)
        proposal = Dev3Proposal(
            proposal_id="p",
            upgrade_id="U01",
            goal="x",
            rationale="x",
            edits=[ProposalEdit(path="tests/test_x.py", operation="append", new_text="#x")],
            expected_effect="x",
            risk_notes=[],
            sources=[],
        )
        verdict = dev7.precheck(proposal=proposal, lock_gate_paths=[])
        self.assertEqual(verdict.verdict, "pass")
