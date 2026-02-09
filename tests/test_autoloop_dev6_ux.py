from unittest import TestCase

from scripts.autoloop.dev6_ux import Dev6UX
from scripts.autoloop.types import Dev3Proposal, ProposalEdit


class AutoloopDev6UXTests(TestCase):
    def test_no_frontend_changes_pass(self) -> None:
        dev6 = Dev6UX()
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
        verdict = dev6.review(proposal=proposal, ux_score_100=60.0)
        self.assertEqual(verdict.verdict, "pass")

    def test_frontend_low_score_warn(self) -> None:
        dev6 = Dev6UX()
        proposal = Dev3Proposal(
            proposal_id="p",
            upgrade_id="U07",
            goal="x",
            rationale="x",
            edits=[ProposalEdit(path="app/frontend/app.js", operation="append", new_text="//x")],
            expected_effect="x",
            risk_notes=[],
            sources=[],
        )
        verdict = dev6.review(proposal=proposal, ux_score_100=50.0)
        self.assertEqual(verdict.verdict, "warn")
