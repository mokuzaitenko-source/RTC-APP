from unittest import TestCase

from scripts.autoloop.dev8_release import Dev8Release


class AutoloopDev8ReleaseTests(TestCase):
    def test_blocks_when_checks_fail(self) -> None:
        dev8 = Dev8Release(require_release_pass=True)
        verdict = dev8.verdict(
            checks_green=False,
            gate_smoke_passed=False,
            gate_stress_passed=False,
            ux_verdict="warn",
        )
        self.assertEqual(verdict.verdict, "block")

    def test_passes_when_all_green(self) -> None:
        dev8 = Dev8Release(require_release_pass=True)
        verdict = dev8.verdict(
            checks_green=True,
            gate_smoke_passed=True,
            gate_stress_passed=True,
            ux_verdict="pass",
        )
        self.assertEqual(verdict.verdict, "pass")
