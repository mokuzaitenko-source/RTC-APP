import os
import tempfile
from pathlib import Path
from unittest import TestCase

from fastapi.testclient import TestClient

from app.backend.main import app
from app.backend.validators.playbook_parser import parse_findings


class ApiContractsTests(TestCase):
	def setUp(self) -> None:
		self._prev_provider_mode = os.environ.get("ASSISTANT_PROVIDER_MODE")
		os.environ["ASSISTANT_PROVIDER_MODE"] = "local"
		self.client = TestClient(app)

	def tearDown(self) -> None:
		if self._prev_provider_mode is None:
			os.environ.pop("ASSISTANT_PROVIDER_MODE", None)
		else:
			os.environ["ASSISTANT_PROVIDER_MODE"] = self._prev_provider_mode

	def test_unknown_finding_state_patch_returns_404(self) -> None:
		response = self.client.patch(
			"/api/findings/F-999/state",
			json={"status": "in_progress"},
		)
		self.assertEqual(response.status_code, 404)
		payload = response.json()
		self.assertFalse(payload["ok"])
		self.assertEqual(payload["error"]["code"], "http_404")

	def test_assistant_respond_returns_clarify_mode_for_ambiguous_prompt(self) -> None:
		response = self.client.post(
			"/api/assistant/respond",
			json={"user_input": "help me make this better"},
		)
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		assistant = payload["data"]["assistant"]
		self.assertEqual(assistant["mode"], "clarify")
		self.assertGreaterEqual(len(assistant["recommended_questions"]), 1)
		self.assertLessEqual(len(assistant["recommended_questions"]), 2)
		self.assertGreaterEqual(assistant["ambiguity_score"], 0.55)

	def test_assistant_respond_returns_plan_execute_for_specific_prompt(self) -> None:
		response = self.client.post(
			"/api/assistant/respond",
			json={
				"user_input": "Design and implement a FastAPI endpoint that validates payload schema and logs test results.",
				"context": "Need deterministic tests and clear error handling.",
				"risk_tolerance": "low",
			},
		)
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		assistant = payload["data"]["assistant"]
		self.assertEqual(assistant["mode"], "plan_execute")
		self.assertGreaterEqual(len(assistant["plan"]), 4)
		self.assertTrue(any("gate" in step.lower() for step in assistant["plan"]))
		self.assertTrue(any("fallback" in step.lower() for step in assistant["plan"]))
		self.assertEqual(assistant["quality"]["revision_required"], False)

	def test_assistant_models_endpoint_returns_catalog(self) -> None:
		response = self.client.get("/api/assistant/models")
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		self.assertIn("models", payload["data"])
		self.assertIn("default_model", payload["data"])
		self.assertIn("provider_mode", payload["data"])
		self.assertGreaterEqual(len(payload["data"]["models"]), 1)

	def test_app_shell_is_assistant_only(self) -> None:
		response = self.client.get("/app")
		self.assertEqual(response.status_code, 200)
		body = response.text
		self.assertIn("Oversight Assistant", body)
		self.assertIn('id="chatForm"', body)
		self.assertIn('id="chatInput"', body)
		self.assertIn('id="chatModel"', body)
		self.assertIn('id="helpOverlay"', body)
		self.assertIn('src="/app/app.js"', body)
		self.assertNotIn("Start Session", body)
		self.assertNotIn("Run Sync", body)
		self.assertNotIn("Run Validate", body)
		self.assertNotIn("Objective Workspace", body)
		self.assertNotIn("Top Actions", body)
		self.assertNotIn('id="opsShell"', body)

	def test_root_route_serves_landing_with_app_cta(self) -> None:
		response = self.client.get("/")
		self.assertEqual(response.status_code, 200)
		body = response.text
		self.assertIn("Oversight Ops Control Room", body)
		self.assertIn("Open Control Room", body)
		self.assertIn('href="/app"', body)

	def test_assistant_respond_auto_mode_without_openai_key_returns_503(self) -> None:
		previous_mode = os.environ.get("ASSISTANT_PROVIDER_MODE")
		previous_key = os.environ.get("OPENAI_API_KEY")
		try:
			os.environ["ASSISTANT_PROVIDER_MODE"] = "auto"
			os.environ.pop("OPENAI_API_KEY", None)
			response = self.client.post(
				"/api/assistant/respond",
				json={"user_input": "Build a release plan for this app."},
			)
		finally:
			if previous_mode is None:
				os.environ.pop("ASSISTANT_PROVIDER_MODE", None)
			else:
				os.environ["ASSISTANT_PROVIDER_MODE"] = previous_mode
			if previous_key is None:
				os.environ.pop("OPENAI_API_KEY", None)
			else:
				os.environ["OPENAI_API_KEY"] = previous_key

		self.assertEqual(response.status_code, 503)
		payload = response.json()
		self.assertFalse(payload["ok"])
		self.assertEqual(payload["error"]["code"], "assistant_provider_unconfigured")


class PlaybookParserTests(TestCase):
	def test_parse_impacted_ids_accepts_req_and_r_prefixes(self) -> None:
		content = """## Wave 1
### F-001
Impacted Requirement IDs:
- `REQ-001`
- `R-2.1-03`
Dependencies:
- `F-002`
"""
		with tempfile.TemporaryDirectory() as tmpdir:
			playbook_path = Path(tmpdir) / "playbook.md"
			playbook_path.write_text(content, encoding="utf-8")
			findings = parse_findings(str(playbook_path))
		self.assertEqual(len(findings), 1)
		self.assertEqual(findings[0].finding_id, "F-001")
		self.assertEqual(findings[0].impacted_req_ids, ["REQ-001", "R-2.1-03"])
		self.assertEqual(findings[0].dependencies, ["F-002"])
