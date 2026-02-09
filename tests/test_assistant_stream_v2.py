import json
import os
from unittest import TestCase

from fastapi.testclient import TestClient

from app.backend.main import app


def _parse_sse_events(raw: str):
	events = []
	for frame in raw.split("\n\n"):
		frame = frame.strip()
		if not frame:
			continue
		event_name = "message"
		data_lines = []
		for line in frame.splitlines():
			if line.startswith("event:"):
				event_name = line.split(":", 1)[1].strip()
			elif line.startswith("data:"):
				data_lines.append(line.split(":", 1)[1].strip())
		data = {}
		if data_lines:
			try:
				data = json.loads("\n".join(data_lines))
			except json.JSONDecodeError:
				data = {"raw": "\n".join(data_lines)}
		events.append((event_name, data))
	return events


class AssistantStreamV2Tests(TestCase):
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

	def test_stream_v2_emits_meta_checkpoint_delta_done(self) -> None:
		with self.client.stream(
			"POST",
			"/api/assistant/stream-v2",
			headers={"X-Session-ID": "stream-v2-1"},
			json={"user_input": "Build a practical implementation plan.", "model": "gpt-4.1-mini"},
		) as response:
			self.assertEqual(response.status_code, 200)
			raw = "".join(response.iter_text())

		events = _parse_sse_events(raw)
		names = [name for name, _ in events]
		self.assertIn("meta", names)
		self.assertIn("checkpoint", names)
		self.assertIn("delta", names)
		self.assertIn("done", names)
		self.assertLess(names.index("meta"), names.index("done"))
		done_data = next(data for name, data in events if name == "done")
		self.assertEqual(done_data.get("aca_version"), "4.1")
		self.assertIn("final_message", done_data)
		self.assertIn(done_data.get("lane_used"), {"quick", "governed"})
		self.assertIsInstance(done_data.get("complexity_reasons"), list)
		self.assertIsInstance(done_data.get("pqs_overall"), (int, float))

	def test_stream_v2_trace_events_when_enabled(self) -> None:
		with self.client.stream(
			"POST",
			"/api/assistant/stream-v2",
			headers={"X-Session-ID": "stream-v2-2", "X-ACA-Trace": "1"},
			json={"user_input": "Build a safe implementation plan.", "model": "gpt-4.1-mini", "trace": True},
		) as response:
			self.assertEqual(response.status_code, 200)
			raw = "".join(response.iter_text())

		events = _parse_sse_events(raw)
		names = [name for name, _ in events]
		self.assertIn("trace", names)
		done_data = next(data for name, data in events if name == "done")
		self.assertIsInstance(done_data.get("trace"), list)
		self.assertGreaterEqual(len(done_data["trace"]), 24)

	def test_stream_v2_invalid_model_emits_error_event(self) -> None:
		with self.client.stream(
			"POST",
			"/api/assistant/stream-v2",
			json={"user_input": "Build plan", "model": "not-allowed"},
		) as response:
			self.assertEqual(response.status_code, 200)
			raw = "".join(response.iter_text())
		events = _parse_sse_events(raw)
		error_data = next(data for name, data in events if name == "error")
		self.assertEqual(error_data.get("code"), "assistant_invalid_model")
