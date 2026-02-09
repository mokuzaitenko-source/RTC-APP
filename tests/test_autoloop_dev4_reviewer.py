from unittest import TestCase

from scripts.autoloop.dev4_reviewer import Dev4Reviewer
from scripts.autoloop.types import Dev3Proposal, ProposalEdit
from scripts.autoloop.upgrade_catalog import get_upgrade_specs


class AutoloopDev4ReviewerTests(TestCase):
    def test_strict_reviewer_requests_revision_for_no_edits(self) -> None:
        reviewer = Dev4Reviewer(policy="strict", research_policy="local_only")
        proposal = Dev3Proposal(
            proposal_id="p1",
            upgrade_id="U01",
            goal="x",
            rationale="x",
            edits=[],
            expected_effect="x",
            risk_notes=[],
            sources=[],
        )
        review = reviewer.review(proposal=proposal, upgrade=get_upgrade_specs()[0])
        self.assertEqual(review.verdict, "revise")

    def test_reviewer_rejects_forbidden_path(self) -> None:
        reviewer = Dev4Reviewer(policy="balanced", research_policy="primary_docs")
        proposal = Dev3Proposal(
            proposal_id="p2",
            upgrade_id="U01",
            goal="x",
            rationale="x",
            edits=[ProposalEdit(path="scripts/run_airtight_gate.py", operation="append", new_text="#x")],
            expected_effect="x",
            risk_notes=[],
            sources=[{"source": "local", "ref": "docs/prompting_book.md"}],
        )
        review = reviewer.review(proposal=proposal, upgrade=get_upgrade_specs()[0])
        self.assertEqual(review.verdict, "rejected")
