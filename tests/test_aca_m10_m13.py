from unittest import TestCase

from app.backend.aca.orchestrator import ACAOrchestrator, ACAOrchestratorHooks
from app.backend.aca.types import ACARequest


def _dummy_build_result(**_kwargs):
	return {
		"mode": "plan_execute",
		"ambiguity_score": 0.2,
		"recommended_questions": [],
		"plan": ["Define scope", "Implement", "Verify", "Fallback policy"],
		"candidate_response": "Proposed execution path:\n1. Define scope\n2. Implement\n3. Verify\n4. Fallback policy",
		"quality": {
			"clarity": 8,
			"completeness": 8,
			"safety": 9,
			"format_compliance": 8,
			"overall": 8.25,
			"revision_required": False,
		},
		"iteration_count": 1,
		"notes": [],
	}


class ACAM10M13Tests(TestCase):
	def _make_request(self, user_input: str) -> ACARequest:
		return ACARequest(
			user_input=user_input,
			context="Must ship in 2 weeks with deterministic tests.",
			risk_tolerance="medium",
			max_questions=2,
			model="gpt-4.1-mini",
			provider_mode="local",
			session_id="m10-m13-test",
			trace_enabled=True,
		)

	def test_m10_to_m13_emit_structured_outputs(self) -> None:
		orchestrator = ACAOrchestrator(ACAOrchestratorHooks(build_result=_dummy_build_result))
		result, _trace = orchestrator.run(self._make_request("Design a practical release plan."))
		module_outputs = result.get("module_outputs", {})
		self.assertIn("M10", module_outputs)
		self.assertIn("M11", module_outputs)
		self.assertIn("M12", module_outputs)
		self.assertIn("M13", module_outputs)
		self.assertIsInstance(module_outputs["M10"].get("constraints"), list)
		self.assertIsInstance(module_outputs["M11"].get("branches"), list)
		self.assertIsInstance(module_outputs["M12"].get("outline"), list)
		self.assertIsInstance(module_outputs["M13"].get("contradictions"), list)
		self.assertIsInstance(result.get("decision_graph"), list)
