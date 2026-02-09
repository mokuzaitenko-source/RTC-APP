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
		self.assertEqual(assistant["lane_used"], "governed")
		self.assertIn("ambiguity_over_threshold", assistant["complexity_reasons"])
		self.assertGreaterEqual(len(assistant["recommended_questions"]), 1)
		self.assertLessEqual(len(assistant["recommended_questions"]), 1)
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
		self.assertEqual(assistant["lane_used"], "quick")
		self.assertGreaterEqual(len(assistant["plan"]), 4)
		self.assertTrue(any("gate" in step.lower() for step in assistant["plan"]))
		self.assertTrue(any("fallback" in step.lower() for step in assistant["plan"]))
		self.assertEqual(assistant["quality"]["revision_required"], False)
		self.assertTrue(str(assistant["candidate_response"]).startswith("Decision:"))

	def test_assistant_models_endpoint_returns_catalog(self) -> None:
		response = self.client.get("/api/assistant/models")
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		self.assertIn("models", payload["data"])
		self.assertIn("default_model", payload["data"])
		self.assertIn("provider_mode", payload["data"])
		self.assertIn("effective_provider_mode", payload["data"])
		self.assertIn("provider_ready", payload["data"])
		self.assertIn("provider_warnings", payload["data"])
		self.assertGreaterEqual(len(payload["data"]["models"]), 1)

	def test_assistant_respond_v2_endpoint_contract(self) -> None:
		response = self.client.post(
			"/api/assistant/respond-v2",
			headers={"X-Session-ID": "api-contract-v2"},
			json={
				"user_input": "Build a practical implementation plan with fallback behavior.",
				"model": "gpt-4.1-mini",
			},
		)
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		data = payload["data"]
		self.assertEqual(data["aca_version"], "4.1")
		self.assertEqual(data["session_id"], "api-contract-v2")
		self.assertIn("module_outputs", data)
		self.assertIn("M10", data["module_outputs"])
		self.assertIn("lane_used", data)
		self.assertIn("complexity_reasons", data)
		self.assertIn("pqs_overall", data)
		self.assertIn("fallback_level", data)
		self.assertIn("assumptions", data)

	def test_assistant_trace_header_adds_aca_trace(self) -> None:
		response = self.client.post(
			"/api/assistant/respond",
			headers={"X-ACA-Trace": "1"},
			json={"user_input": "Build a practical milestone plan."},
		)
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		self.assertIn("aca_trace", payload["data"])
		self.assertIsInstance(payload["data"]["aca_trace"], list)
		self.assertGreaterEqual(len(payload["data"]["aca_trace"]), 24)

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

	def test_assistant_respond_auto_mode_without_openai_key_falls_back_to_local(self) -> None:
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

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		assistant = payload["data"]["assistant"]
		self.assertEqual(assistant["provider_mode"], "local")

	def test_assistant_respond_risk_sensitive_request_uses_governed_lane(self) -> None:
		response = self.client.post(
			"/api/assistant/respond",
			json={
				"user_input": "Design production auth and payment rollout with policy and legal safeguards.",
				"risk_tolerance": "medium",
			},
		)
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		assistant = payload["data"]["assistant"]
		self.assertEqual(assistant["lane_used"], "governed")
		self.assertIn("risk_domain_signal", assistant["complexity_reasons"])

	def test_assistant_respond_forced_quick_override_is_honored(self) -> None:
		response = self.client.post(
			"/api/assistant/respond",
			json={"user_input": "quick only: build me a short execution summary"},
		)
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		assistant = payload["data"]["assistant"]
		self.assertEqual(assistant["lane_used"], "quick")
		self.assertIn("forced_quick_only", assistant["complexity_reasons"])

	def test_assistant_respond_forced_governed_override_is_honored(self) -> None:
		response = self.client.post(
			"/api/assistant/respond",
			json={"user_input": "full governed: generate rollout plan"},
		)
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertTrue(payload["ok"])
		assistant = payload["data"]["assistant"]
		self.assertEqual(assistant["lane_used"], "governed")
		self.assertIn("forced_full_governed", assistant["complexity_reasons"])


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
