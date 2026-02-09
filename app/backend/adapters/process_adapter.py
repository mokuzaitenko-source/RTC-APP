from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from typing import Dict


def _now_iso() -> str:
	return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_sync_process() -> Dict[str, str | int]:
	started_at = _now_iso()
	try:
		proc = subprocess.run(
			[
				sys.executable,
				"scripts/sync_oversight_trace.py",
				"--rfc",
				"docs/oversight_assistant_rfc.md",
				"--matrix",
				"docs/requirements_trace_matrix.md",
				"--playbook",
				"docs/patch_playbook.md",
				"--handoff",
				"SESSION_HANDOFF.md",
			],
			capture_output=True,
			text=True,
			timeout=120,
		)
		exit_code = proc.returncode
		stdout = proc.stdout
		stderr = proc.stderr
	except subprocess.TimeoutExpired:
		exit_code = 124
		stdout = ""
		stderr = "sync process timed out after 120 seconds"
	ended_at = _now_iso()
	return {
		"exit_code": exit_code,
		"stdout": stdout,
		"stderr": stderr,
		"started_at": started_at,
		"ended_at": ended_at,
	}
