# Layer 2 Validator Implementation Spec (Local Oversight App v1)

## Goal / Non-goals

Goal: lock deterministic validator behavior, evidence output, and failure payloads for the local oversight app.
Non-goals: UI rendering, action queue ranking logic, or any doc mutation behavior.

Related spec: docs/specs/oversight_ops_app_v1_layer2.md
Related fixture spec: docs/specs/oversight_ops_app_v1_layer2_validator_fixtures.md

## Backend Module Layout

- app/backend/validators/
  - __init__.py
  - engine.py (run_all_validators orchestrator)
  - sources.py (load/parse RFC, matrix, playbook, handoff)
  - rules.py (invariant implementations)
  - evidence.py (evidence builders + deterministic sorting)
  - types.py (dataclasses / pydantic models)

## Canonical Types and Schemas

### EvidenceItem

- kind: file_line | id_list | summary | diff
- ref: string
- detail: string
- hash: string | null (for normalized line hashing)

### InvariantResult

- id: string
- status: pass | fail
- message: string (one sentence, UI-safe)
- evidence: list[EvidenceItem]
- recommended_action: string

### ValidatorReport

- run_id: string
- run_type: validate
- status: pass | fail
- started_at: iso8601
- ended_at: iso8601
- invariants: list[InvariantResult]
- summary: string

## Deterministic Evidence + Normalization Rules

### Evidence ordering

- file_line items sorted by path asc, then line asc.
- id_list items sorted by id asc.
- diff items sorted by ref asc.
- summary items last.

### Stable set-diff encoding

- Use: "missing=[A,B]; extra=[C]" with both lists sorted asc.
- Empty list rendered as [] (not omitted).

### Stable hashing for normalized lines

- normalized_line = trim, collapse whitespace to single spaces.
- hash format: sha256:<hex> (lowercase hex).

## Parsing Contracts

### RFC normative extractor

- Source: docs/oversight_assistant_rfc.md
- Match whole-word tokens MUST, SHALL, SHOULD, MAY.
- Ignore fenced code blocks and headings (lines starting with #).
- Emit for each line:
  - rfc_line_id: RFC:<line_number>
  - normative_level: MUST | SHALL | SHOULD | MAY
  - text: trimmed line
  - hash: sha256 of normalized_line

### Matrix parser

- Source: docs/requirements_trace_matrix.md
- Parse the Core Requirement Trace table rows only.
- Emit for each row:
  - req_id
  - status (covered | partial | gap)
  - findings (list parsed from Finding column)
  - enforcement_tbd (true if enforcement point contains TBD)
  - proof_tbd (true if proof/test column contains TBD)
  - source_ref (path:line if resolvable)

### Playbook parser

- Source: docs/patch_playbook.md
- Parse finding sections F-001 ... F-016.
- Emit:
  - finding_id
  - dependencies (explicit dependency list if present, else empty)
  - impacted_req_ids (from integration guidance or explicit trace notes)

### Handoff parser

- Source: SESSION_HANDOFF.md
- Parse wave-1 blocker list.
- Parse authoritative counts for parity cross-check logging only.

## Invariant Engine Contract

### run_all_validators behavior

- All invariants run even if earlier invariants fail.
- Output ordering is fixed:
  1) toolchain_ok
  2) parity
  3) no_orphan_must
  4) finding_integrity
  5) backlink_consistency
  6) blocker_pin
  7) state_integrity
- Deterministic outputs for identical inputs (byte-identical messages and evidence lists).

### Failure payload constraints

- message is one sentence, no stack traces.
- details go only in evidence/logs.
- run-validate returns 200 for invariant failures; 500 only for engine or parser crash.

## Function-Level Invariant Behavior

### toolchain_ok

- Pass if last sync and last validate exit codes are zero.
- Fail if records missing or any non-zero exit code.
- Evidence: run log references and exit codes.

### parity

- Count RFC normative lines.
- Count matrix core rows.
- Pass if counts equal, else fail with counts and sample line refs.

### no_orphan_must (hybrid mapping)

Config: orphan_mapping_mode = source_line | req_tag_strict
Default: source_line

- source_line mode (v1):
  - For each RFC MUST/SHALL line, confirm at least one matrix core row Source matches RFC:<line_number>.
  - Fail with orphan RFC line ids.
- req_tag_strict mode (future):
  - Requires REQ-### tags on RFC normative lines.
  - Matrix rows must map via matching REQ-### tags.
  - Fail when tags are missing or unmapped.

### finding_integrity

- Every matrix row with status gap or partial must list at least one finding id.
- Fail with req_id list.

### backlink_consistency

- For each finding:
  - Matrix rows referencing finding must match playbook impacted_req_ids.
- Compare sets exactly; fail with diff evidence.

### blocker_pin

- Wave-1 blocker IDs from SESSION_HANDOFF must exist in playbook and be marked as blockers.
- Fail with missing or unmarked IDs.

### state_integrity

- All app state finding_id values must exist in playbook.
- Status must be one of: unstarted | in_progress | blocked | ready_for_validation.
- Fail with unknown ids and invalid statuses.

## API Payload Contracts (validator outputs)

### POST /api/ops/run-validate

Returns ValidatorReport. Status is fail if any invariant fails.

### POST /api/session/start

- Runs sync then validate.
- Returns run_events + invariants (ValidatorReport.invariants) + action queue.

## Action Queue Dependency Rules (from invariants)

- If toolchain_ok fails, only remediation cards (run_sync/run_validate) are allowed.
- If parity or no_orphan_must fails, repair_invariant cards precede non-blocker work.
- If backlink_consistency fails, repair_invariant cards must reference impacted findings.

## Test Matrix

### Determinism

- Identical inputs -> byte-identical invariant ordering and evidence ordering.

### no_orphan_must

- source_line mode pass and fail fixtures.
- req_tag_strict mode fails when tags absent.

### Contract behavior

- 200 on validation failures.
- 500 on parser/engine crash only.

### Backlink and blocker pin

- Validate against current canonical files (RFC, matrix, playbook, handoff).

## Config Constants and Defaults

- orphan_mapping_mode = source_line (default)
- evidence_hash_algo = sha256
- invariant_order = [toolchain_ok, parity, no_orphan_must, finding_integrity, backlink_consistency, blocker_pin, state_integrity]

## Migration Note: REQ-Tag Strict Mode

When RFC normative lines include REQ-### tags and the matrix Source column maps those tags, switch orphan_mapping_mode to req_tag_strict. Until then, source_line is the required v1 default.

## Assumptions and Defaults

- Canonical docs remain the source of truth.
- Current requirement IDs are R-* and matrix source-line references are available.
- RFC does not provide complete REQ-### tagging in v1.
- App remains local-first, single-user, and non-mutating for validation operations.
