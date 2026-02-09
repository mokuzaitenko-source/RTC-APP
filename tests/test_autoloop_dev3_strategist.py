from unittest import TestCase

from scripts.autoloop.dev3_strategist import Dev3Strategist
from scripts.autoloop.upgrade_catalog import get_upgrade_specs


class AutoloopDev3StrategistTests(TestCase):
    def test_local_mode_generates_proposal_without_key(self) -> None:
        dev3 = Dev3Strategist(mode="local", research_policy="primary_docs")
        proposal = dev3.propose(
            cycle=1,
            technique="Task Decomposition",
            weakest_dimension="workflow",
            latest_scores={"workflow": 50.0, "reliability": 60.0, "ux": 70.0},
            upgrade=get_upgrade_specs()[0],
            model="gpt-4.1-mini",
            dry_run=False,
            proposal_generator=None,
        )
        self.assertEqual(proposal.upgrade_id, "U01")
        self.assertGreaterEqual(len(proposal.sources), 1)

    def test_cloud_mode_uses_generator_payload(self) -> None:
        dev3 = Dev3Strategist(mode="cloud", research_policy="primary_docs")
        proposal = dev3.propose(
            cycle=1,
            technique="Task Decomposition",
            weakest_dimension="workflow",
            latest_scores={"workflow": 50.0, "reliability": 60.0, "ux": 70.0},
            upgrade=get_upgrade_specs()[0],
            model="gpt-4.1-mini",
            dry_run=False,
            proposal_generator=lambda prompt, model, dry_run: {
                "goal": "Improve U01",
                "rationale": "x",
                "edits": [{"path": "tests/test_a.py", "operation": "append", "new_text": "#x\n"}],
                "expected_effect": "x",
                "risk_notes": [],
            },
        )
        self.assertEqual(proposal.goal, "Improve U01")
        self.assertEqual(len(proposal.edits), 1)
