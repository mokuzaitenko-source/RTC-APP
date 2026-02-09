import os
from unittest import TestCase
from unittest.mock import patch

from app.backend.services import assistant_service


class _FakeResponses:
	def __init__(self, *, output_text: str | None = None, error: Exception | None = None):
		self._output_text = output_text
		self._error = error

	def create(self, **_kwargs):
		if self._error is not None:
			raise self._error
		return type("FakeResponse", (), {"output_text": self._output_text})()


class _FakeClient:
	def __init__(self, *, output_text: str | None = None, error: Exception | None = None):
		self.responses = _FakeResponses(output_text=output_text, error=error)


class AssistantProviderTests(TestCase):
	def test_openai_provider_success_returns_contract_shape(self) -> None:
		payload = """
		{
		  "mode": "plan_execute",
		  "recommended_questions": [],
		  "plan": ["Define scope", "Implement endpoint", "Add tests", "Verify outputs"],
		  "candidate_response": "Proposed execution path:\\n1. Define scope\\n2. Implement endpoint\\n3. Add tests\\n4. Verify outputs",
		  "notes": ["provider:openai"],
		  "iteration_count": 1
		}
		"""
		client = _FakeClient(output_text=payload)
		with patch.dict(
			os.environ,
			{
				"ASSISTANT_PROVIDER_MODE": "openai",
				"OPENAI_API_KEY": "test-key",
				"ASSISTANT_OPENAI_MODELS": "gpt-4.1-mini,gpt-4o-mini",
			},
			clear=False,
		), patch("app.backend.services.assistant_service._build_openai_client", return_value=client):
			result = assistant_service.respond(
				user_input="Design and implement a FastAPI endpoint that validates payload schema and logs test results.",
				context="Need deterministic tests and clear error handling.",
				risk_tolerance="low",
				max_questions=2,
				model="gpt-4.1-mini",
			)

		self.assertEqual(result["mode"], "plan_execute")
		self.assertGreaterEqual(len(result["plan"]), 4)
		self.assertIn("quality", result)
		self.assertIn("candidate_response", result)
		self.assertEqual(result["recommended_questions"], [])
		self.assertTrue(any("gate" in step.lower() for step in result["plan"]))
		self.assertTrue(any("fallback" in step.lower() for step in result["plan"]))

	def test_invalid_model_rejected_by_allowlist(self) -> None:
		with patch.dict(
			os.environ,
			{"ASSISTANT_PROVIDER_MODE": "local", "ASSISTANT_OPENAI_MODELS": "gpt-4.1-mini"},
			clear=False,
		):
			with self.assertRaises(assistant_service.AssistantServiceError) as ctx:
				assistant_service.respond(
					user_input="Create a release plan",
					model="gpt-unknown",
				)
		self.assertEqual(ctx.exception.status_code, 400)
		self.assertEqual(ctx.exception.code, "assistant_invalid_model")

	def test_conversation_intent_routes_to_single_clarify(self) -> None:
		with patch.dict(
			os.environ,
			{"ASSISTANT_PROVIDER_MODE": "local", "ASSISTANT_OPENAI_MODELS": "gpt-4.1-mini"},
			clear=False,
		):
			result = assistant_service.respond(user_input="hi")
		self.assertEqual(result.get("mode"), "clarify")
		self.assertEqual(result.get("interaction_mode"), "conversation")
		questions = result.get("recommended_questions")
		self.assertIsInstance(questions, list)
		self.assertLessEqual(len(questions), 1)
		self.assertTrue(str(result.get("candidate_response", "")).strip().startswith("Tell me one concrete thing"))

	def test_conversation_question_returns_conversation_clarify(self) -> None:
		with patch.dict(
			os.environ,
			{"ASSISTANT_PROVIDER_MODE": "local", "ASSISTANT_OPENAI_MODELS": "gpt-4.1-mini"},
			clear=False,
		):
			result = assistant_service.respond(user_input="can we chat?")
		self.assertEqual(result.get("mode"), "clarify")
		self.assertEqual(result.get("interaction_mode"), "conversation")
		self.assertLessEqual(len(result.get("recommended_questions", [])), 1)

	def test_requested_five_step_plan_is_enforced(self) -> None:
		with patch.dict(
			os.environ,
			{"ASSISTANT_PROVIDER_MODE": "local", "ASSISTANT_OPENAI_MODELS": "gpt-4.1-mini"},
			clear=False,
		):
			result = assistant_service.respond(
				user_input="Turn my goal into a 5-step execution plan with acceptance checks.",
				context="Goal: ship an MVP quickly",
			)
		self.assertEqual(result.get("mode"), "plan_execute")
		plan = result.get("plan")
		self.assertIsInstance(plan, list)
		self.assertEqual(len(plan), 5)
		self.assertFalse(any("verify" in str(step).lower() or "fallback" in str(step).lower() for step in plan[:3]))
		self.assertTrue("verify" in str(plan[3]).lower() or "gate" in str(plan[3]).lower())
		self.assertIn("fallback", str(plan[4]).lower())
		candidate = str(result.get("candidate_response", ""))
		self.assertIn("1.", candidate)
		self.assertIn("5.", candidate)
		self.assertNotIn("6.", candidate)

	def test_model_catalog_returns_allowlist(self) -> None:
		with patch.dict(
			os.environ,
			{"ASSISTANT_PROVIDER_MODE": "local", "ASSISTANT_OPENAI_MODELS": "gpt-4.1-mini,gpt-4o-mini"},
			clear=False,
		):
			catalog = assistant_service.list_models()
		self.assertEqual(catalog["provider_mode"], "local")
		self.assertEqual(catalog["effective_provider_mode"], "local")
		self.assertTrue(catalog["provider_ready"])
		self.assertEqual(catalog["provider_warnings"], [])
		self.assertEqual(catalog["default_model"], "gpt-4.1-mini")
		self.assertEqual(catalog["models"], ["gpt-4.1-mini", "gpt-4o-mini"])

	def test_model_catalog_openai_without_key_reports_not_ready(self) -> None:
		with patch.dict(
			os.environ,
			{"ASSISTANT_PROVIDER_MODE": "openai", "ASSISTANT_OPENAI_MODELS": "gpt-4.1-mini"},
			clear=False,
		):
			os.environ.pop("OPENAI_API_KEY", None)
			catalog = assistant_service.list_models()
		self.assertEqual(catalog["provider_mode"], "openai")
		self.assertEqual(catalog["effective_provider_mode"], "openai")
		self.assertFalse(catalog["provider_ready"])
		self.assertGreaterEqual(len(catalog["provider_warnings"]), 1)

	def test_model_catalog_auto_without_key_reports_local_effective_mode(self) -> None:
		with patch.dict(
			os.environ,
			{"ASSISTANT_PROVIDER_MODE": "auto", "ASSISTANT_OPENAI_MODELS": "gpt-4.1-mini"},
			clear=False,
		):
			os.environ.pop("OPENAI_API_KEY", None)
			catalog = assistant_service.list_models()
		self.assertEqual(catalog["provider_mode"], "auto")
		self.assertEqual(catalog["effective_provider_mode"], "local")
		self.assertTrue(catalog["provider_ready"])

	def test_openai_provider_invalid_json_raises_provider_error(self) -> None:
		client = _FakeClient(output_text="not-json")
		with patch.dict(
			os.environ,
			{"ASSISTANT_PROVIDER_MODE": "openai", "OPENAI_API_KEY": "test-key"},
			clear=False,
		), patch("app.backend.services.assistant_service._build_openai_client", return_value=client):
			with self.assertRaises(assistant_service.AssistantServiceError) as ctx:
				assistant_service.respond(
					user_input="Create a release plan",
					context=None,
					risk_tolerance="medium",
					max_questions=2,
				)
		self.assertEqual(ctx.exception.status_code, 502)
		self.assertEqual(ctx.exception.code, "assistant_provider_error")

	def test_openai_provider_timeout_maps_to_504(self) -> None:
		class APITimeoutError(Exception):
			pass

		client = _FakeClient(error=APITimeoutError("timeout"))
		with patch.dict(
			os.environ,
			{"ASSISTANT_PROVIDER_MODE": "openai", "OPENAI_API_KEY": "test-key"},
			clear=False,
		), patch("app.backend.services.assistant_service._build_openai_client", return_value=client):
			with self.assertRaises(assistant_service.AssistantServiceError) as ctx:
				assistant_service.respond(
					user_input="Create a release plan",
					context=None,
					risk_tolerance="medium",
					max_questions=2,
				)
		self.assertEqual(ctx.exception.status_code, 504)
		self.assertEqual(ctx.exception.code, "assistant_provider_timeout")

	def test_openai_provider_api_error_maps_to_502(self) -> None:
		class APIError(Exception):
			pass

		client = _FakeClient(error=APIError("api failure"))
		with patch.dict(
			os.environ,
			{"ASSISTANT_PROVIDER_MODE": "openai", "OPENAI_API_KEY": "test-key"},
			clear=False,
		), patch("app.backend.services.assistant_service._build_openai_client", return_value=client):
			with self.assertRaises(assistant_service.AssistantServiceError) as ctx:
				assistant_service.respond(
					user_input="Create a release plan",
					context=None,
					risk_tolerance="medium",
					max_questions=2,
				)
		self.assertEqual(ctx.exception.status_code, 502)
		self.assertEqual(ctx.exception.code, "assistant_provider_error")
