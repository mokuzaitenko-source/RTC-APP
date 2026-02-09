import os
from unittest import TestCase

from fastapi.testclient import TestClient

from app.backend.main import app


class ACATraceApiTests(TestCase):
	def setUp(self) -> None:
		self.client = TestClient(app)
		self._prev_mode = os.environ.get("ASSISTANT_PROVIDER_MODE")
		self._prev_enabled = os.environ.get("ASSISTANT_ACA_ENABLED")
		os.environ["ASSISTANT_PROVIDER_MODE"] = "local"
		os.environ["ASSISTANT_ACA_ENABLED"] = "1"

	def tearDown(self) -> None:
		if self._prev_mode is None:
			os.environ.pop("ASSISTANT_PROVIDER_MODE", None)
		else:
			os.environ["ASSISTANT_PROVIDER_MODE"] = self._prev_mode
		if self._prev_enabled is None:
			os.environ.pop("ASSISTANT_ACA_ENABLED", None)
		else:
			os.environ["ASSISTANT_ACA_ENABLED"] = self._prev_enabled

	def test_trace_disabled_by_default(self) -> None:
		response = self.client.post("/api/assistant/respond", json={"user_input": "Create a practical plan."})
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		self.assertNotIn("aca_trace", payload["data"])

	def test_trace_enabled_returns_module_timeline(self) -> None:
		response = self.client.post(
			"/api/assistant/respond",
			headers={"X-ACA-Trace": "1"},
			json={"user_input": "Build a robust feature plan with safe fallback."},
		)
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		trace = payload["data"].get("aca_trace")
		self.assertIsInstance(trace, list)
		self.assertGreaterEqual(len(trace), 24)
		self.assertEqual(trace[0]["module_id"], "M0")
		self.assertEqual(trace[-1]["module_id"], "M23")

