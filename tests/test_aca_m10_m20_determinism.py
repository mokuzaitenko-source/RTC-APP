from unittest import TestCase

from app.backend.aca.orchestrator import ACAOrchestrator, ACAOrchestratorHooks
from app.backend.aca.types import ACARequest


def _stable_result(**_kwargs):
	return {
		"mode": "plan_execute",
		"ambiguity_score": 0.15,
		"recommended_questions": [],
		"plan": [
			"Input gate: confirm scope",
			"Implement the minimal slice",
			"Acceptance check: run tests",
			"Fallback policy: retry with simplified strategy",
		],
		"candidate_response": "Proposed execution path:\n1. Input gate\n2. Implement\n3. Acceptance check\n4. Fallback policy",
		"quality": {
			"clarity": 9,
			"completeness": 9,
			"safety": 9,
			"format_compliance": 9,
			"overall": 9.0,
			"revision_required": False,
		},
		"iteration_count": 1,
		"notes": [],
	}


class ACADeterminismTests(TestCase):
	def _request(self) -> ACARequest:
		return ACARequest(
			user_input="Design and implement deterministic assistant workflow.",
			context="Need acceptance checks and fallback behavior.",
			risk_tolerance="medium",
			max_questions=2,
			model="gpt-4.1-mini",
			provider_mode="local",
			session_id="determinism-session",
			trace_enabled=True,
		)

	def test_m10_m20_outputs_are_deterministic(self) -> None:
		orchestrator = ACAOrchestrator(ACAOrchestratorHooks(build_result=_stable_result))
		result_a, _trace_a = orchestrator.run(self._request())
		result_b, _trace_b = orchestrator.run(self._request())
		for module_id in [f"M{index}" for index in range(10, 21)]:
			self.assertEqual(result_a["module_outputs"][module_id], result_b["module_outputs"][module_id])
