# app/backend/validators/engine.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from app.backend import constants
from .backlink_consistency import check as check_backlink_consistency
from .blocker_pin import check as check_blocker_pin
from .finding_integrity import check as check_finding_integrity
from .no_orphan_must import check as check_no_orphan_must
from .parity import check as check_parity
from .state_integrity import check as check_state_integrity
from .toolchain_ok import check as check_toolchain_ok
from .types import InvariantResult, ValidatorContext, ValidatorReport


def run_all_validators(ctx: ValidatorContext) -> ValidatorReport:
	started_at = datetime.now(timezone.utc)
	checks = {
		"toolchain_ok": check_toolchain_ok,
		"parity": check_parity,
		"no_orphan_must": check_no_orphan_must,
		"finding_integrity": check_finding_integrity,
		"backlink_consistency": check_backlink_consistency,
		"blocker_pin": check_blocker_pin,
		"state_integrity": check_state_integrity,
	}
	invariants: List[InvariantResult] = [checks[name](ctx) for name in constants.INVARIANT_ORDER]
	status = "pass" if all(inv.status == "pass" for inv in invariants) else "fail"
	summary = "All invariants passed." if status == "pass" else "One or more invariants failed."
	ended_at = datetime.now(timezone.utc)
	return ValidatorReport(
		run_id=str(uuid.uuid4()),
		run_type="validate",
		status=status,
		started_at=started_at,
		ended_at=ended_at,
		invariants=invariants,
		summary=summary,
	)

