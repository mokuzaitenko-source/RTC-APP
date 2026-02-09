from unittest import TestCase

from scripts.autoloop.upgrade_catalog import UPGRADE_IDS, get_next_upgrade, get_upgrade_specs, success_predicate_met


class AutoloopUpgradeCatalogTests(TestCase):
    def test_upgrade_catalog_has_10_ids(self) -> None:
        specs = get_upgrade_specs()
        self.assertEqual(len(specs), 10)
        self.assertEqual([spec.upgrade_id for spec in specs], UPGRADE_IDS)

    def test_next_upgrade_skips_accepted(self) -> None:
        next_spec = get_next_upgrade(["U01", "U02"])
        self.assertIsNotNone(next_spec)
        self.assertEqual(next_spec.upgrade_id, "U03")

    def test_success_predicate_uses_eval_and_gate(self) -> None:
        spec = get_upgrade_specs()[0]
        ok = success_predicate_met(
            upgrade=spec,
            workflow_eval={"score_100": 90.0},
            ux_eval={"score_100": 90.0},
            gate_result={
                "overall_x": 10.0,
                "checks_pass": True,
                "gate_smoke_passed": True,
                "gate_stress_passed": True,
            },
            checks_pass=True,
        )
        self.assertTrue(ok)
