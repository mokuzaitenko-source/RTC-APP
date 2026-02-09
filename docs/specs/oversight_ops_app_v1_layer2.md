# Layer 2 Spec: Validator Engine + Deterministic Action Queue (Local Oversight App v1)

## Summary

Descend next into validator definitions and lock the runtime contracts that make the app reliable: deterministic invariants, deterministic ranking, and strict progress semantics.

## Chosen Constraints

- Layer focus: domain model + ranking.
- Priority method: tiered deterministic rules.
- App-state store: local SQLite.
- Canonical truth remains docs/files; app DB stores state only.
- Related validator spec: docs/specs/oversight_ops_app_v1_layer2_validators.md

## Important Public Interfaces / Types

### FindingState (SQLite-backed app state)

- finding_id: str (PK)
- status: unstarted | in_progress | blocked | ready_for_validation
- note: str | null
- updated_at: datetime
- last_seen_hash: str | null (optional drift hint)

### RequirementReadModel (derived from matrix)

- req_id: str
- status: covered | partial | gap
- normative_level: MUST | SHALL | SHOULD | MAY
- enforcement_tbd: bool
- proof_tbd: bool
- linked_findings: list[str]
- source_ref: str (path:line when line known)

### FindingReadModel (derived from playbook + matrix + app state)

- finding_id: str
- is_wave1_blocker: bool
- dependencies: list[str]
- impacted_req_ids: list[str]
- impact_count: int
- app_status: FindingState.status

### InvariantResult

- id: str (toolchain_ok, parity, no_orphan_must, finding_integrity, backlink_consistency, blocker_pin, state_integrity)
- status: pass | fail
- message: str
- evidence: list[str] (paths/IDs)
- recommended_action: str

### ActionCard

- action_id: str (stable hash)
- tier: int
- type: resolve_blocker | run_sync | run_validate | repair_invariant | triage_section | export_status
- target: str
- title: str
- why_now: str (deterministic explanation)
- steps: list[str]
- commands: list[str]
- links: list[str]

## Backend API Contracts (v1)

- POST /api/session/start
  - Runs sync then validate, computes queue, returns top_actions, invariants, run_events.
- POST /api/ops/run-sync
  - Executes sync_oversight_trace.py; returns structured run event.
- POST /api/ops/run-validate
  - Runs invariant engine only (non-mutating); returns full invariant list.
- GET /api/actions/next?limit=10
  - Returns deterministic queue sorted by tier/tie-breakers.
- GET /api/findings and GET /api/findings/{id}
  - Includes dependencies, impacted reqs, app state, and proof expectations.
- PATCH /api/findings/{id}/state
  - Allowed transitions only among the four states; no "done".

## Deterministic Ranking Algorithm

### Tier 0: Toolchain hard-fail

If last sync/validate failed, only remediation cards appear (run_sync/run_validate + log view).

### Tier 1: Wave-1 unresolved blockers

Fixed blocker set: F-001, F-002, F-003, F-004, F-007, F-009.
Include blockers not in ready_for_validation.

### Tier 2: Ready-for-validation gate

If any finding is ready_for_validation, prioritize run_validate.
This tier always precedes Tier 3 when both are present.

### Tier 3: Invariant repair

If any invariant fails, queue repair_invariant cards before non-blocker work.

### Tier 4: Non-blocker findings by impact

Highest impacted requirement count first.

### Tier 5: F-016 section triage

Batch by section density (gap/partial concentration).

### Tie-breakers within a tier (strict order)

1. Dependency unblock count (higher first)
2. Impact count (higher first)
3. Normative severity touched (MUST/SHALL > SHOULD > MAY)
4. Stable lexical ID (ascending)

#### Dependency unblock count (precise)

The number of findings that list the target finding as a dependency where all other dependencies for those findings are already satisfied. Count only findings that would become unblocked if this target were completed.

## Validator Definitions (Non-Mutating)

### toolchain_ok

Last sync + validate exit codes are zero.

### parity

RFC normative line count equals matrix core requirement row count.
Source: docs/oversight_assistant_rfc.md. Use the same normalization rules as sync_oversight_trace.py. For v1, count lines containing whole-word MUST/SHALL/SHOULD/MAY outside fenced code blocks and ignore headings.

### no_orphan_must

Every RFC MUST/SHALL line maps to at least one core requirement row.
Use the same normalization and line-source rules as parity.

### finding_integrity

Every gap/partial requirement has at least one finding.

### backlink_consistency

Matrix finding backlinks and playbook impacted IDs are exact set matches.

### blocker_pin

All Wave-1 blocker IDs exist and remain classed as blockers.

### state_integrity

All app finding statuses are in allowed enum; no unknown finding IDs in DB. If a DB finding_id does not exist in the playbook, fail with evidence listing the unknown IDs.

## Progress-State Semantics (No Hanging Parts)

### Allowed states only

- unstarted
- in_progress
- blocked
- ready_for_validation

No manual done.
Completion is derived: relevant invariants pass + finding no longer violates blocker conditions.

### Transition rules

- unstarted -> in_progress | blocked
- in_progress -> blocked | ready_for_validation
- blocked -> in_progress
- ready_for_validation -> in_progress (if regression found)

## Source Linking Format (Windows-safe)

Use workspace-relative path:line where line is known.
Fallback to path only when line cannot be resolved.
All action cards must include at least one resolvable file link.

## Test Cases and Scenarios

### Determinism

Same inputs produce byte-identical action ordering and why_now lines.

### Tier correctness

Any sync/validate failure suppresses non-remediation cards.

### Blocker precedence

Unresolved Wave-1 blockers always outrank F-016 triage.

### Backlink mismatch detection

Playbook/matrix divergence fails backlink_consistency with exact IDs.

### Parity failure detection

Off-by-one normative/core rows fails parity.

### Progress integrity

Invalid state value rejected; illegal transition rejected.

### Derived completion behavior

No API path can set done; completion appears only via derived pass state.

### Deep-link validity

Every queued card has at least one existing file path link.

## Assumptions and Defaults

- Local single-user runtime.
- SQLite file at oversight_state.db.
- Canonical docs remain source of truth; app DB is state overlay only.
- Existing sync_oversight_trace.py stays the only mutating generator for docs.
- Chat UI is deferred beyond v1.
