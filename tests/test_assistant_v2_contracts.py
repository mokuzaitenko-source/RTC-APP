import os
from unittest import TestCase

from fastapi.testclient import TestClient

from app.backend.main import app


class AssistantV2ContractTests(TestCase):
	def setUp(self) -> None:
		self.client = TestClient(app)
		self._prev_mode = os.environ.get("ASSISTANT_PROVIDER_MODE")
		self._prev_models = os.environ.get("ASSISTANT_OPENAI_MODELS")
		os.environ["ASSISTANT_PROVIDER_MODE"] = "local"
		os.environ["ASSISTANT_OPENAI_MODELS"] = "gpt-4.1-mini"

	def tearDown(self) -> None:
		if self._prev_mode is None:
			os.environ.pop("ASSISTANT_PROVIDER_MODE", None)
		else:
			os.environ["ASSISTANT_PROVIDER_MODE"] = self._prev_mode
		if self._prev_models is None:
			os.environ.pop("ASSISTANT_OPENAI_MODELS", None)
		else:
			os.environ["ASSISTANT_OPENAI_MODELS"] = self._prev_models

	def test_respond_v2_returns_versioned_schema(self) -> None:
		response = self.client.post(
			"/api/assistant/respond-v2",
			headers={"X-Session-ID": "v2-contract-session"},
			json={
				"user_input": "Design a 2-week MVP plan with acceptance checks and fallback behavior.",
				"risk_tolerance": "medium",
				"model": "gpt-4.1-mini",
			},
		)
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		data = payload["data"]
		self.assertEqual(data["aca_version"], "4.1")
		self.assertEqual(data["session_id"], "v2-contract-session")
		self.assertIn(data["mode"], {"clarify", "plan_execute"})
		self.assertIn("final_message", data)
		self.assertIsInstance(data.get("decision_graph"), list)
		self.assertIsInstance(data.get("module_outputs"), dict)
		self.assertIn("M10", data["module_outputs"])
		self.assertIn("M20", data["module_outputs"])
		self.assertIsInstance(data.get("quality"), dict)
		self.assertIsInstance(data.get("safety"), dict)
		self.assertIsInstance(data.get("fallback"), dict)

	def test_respond_v2_trace_enabled_by_payload(self) -> None:
		response = self.client.post(
			"/api/assistant/respond-v2",
			headers={"X-Session-ID": "v2-trace-session"},
			json={"user_input": "Create implementation plan.", "trace": True, "model": "gpt-4.1-mini"},
		)
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		data = payload["data"]
		self.assertIn("trace", data)
		self.assertIsInstance(data["trace"], list)
		self.assertGreaterEqual(len(data["trace"]), 24)

	def test_respond_v2_invalid_model_rejected(self) -> None:
		response = self.client.post(
			"/api/assistant/respond-v2",
			json={"user_input": "Create implementation plan.", "model": "not-allowed"},
		)
		self.assertEqual(response.status_code, 400)
		payload = response.json()
		self.assertFalse(payload["ok"])
		self.assertEqual(payload["error"]["code"], "assistant_invalid_model")
