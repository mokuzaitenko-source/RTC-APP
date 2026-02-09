# Backend Skeleton + TODO Map (Local Oversight App v1)

## Scope and Non-goals

Scope: define backend module skeleton, responsibilities, function signatures, and TODO map aligned to Layer 2 validators and Layer 3 API contracts.
Non-goals: frontend UI, deployment, or mutation of canonical docs beyond sync_oversight_trace.py.

Related specs:

- docs/specs/oversight_ops_app_v1_layer2.md
- docs/specs/oversight_ops_app_v1_layer2_validators.md
- docs/specs/oversight_ops_app_v1_layer3_api_contracts.md

## Final Backend Directory Tree

- app/backend/
  - main.py
  - routers/
    - session.py
    - ops.py
    - findings.py
    - requirements.py
    - health.py
    - export.py
  - services/
    - session_service.py
    - action_queue_service.py
    - health_service.py
    - state_service.py
  - adapters/
    - docs_adapter.py
    - process_adapter.py
    - sqlite_adapter.py
  - validators/
    - engine.py
    - types.py
    - evidence.py
    - rfc_normative.py
    - matrix_parser.py
    - playbook_parser.py
    - toolchain_ok.py
    - parity.py
    - no_orphan_must.py
    - finding_integrity.py
    - backlink_consistency.py
    - blocker_pin.py
    - state_integrity.py
  - constants.py
  - schemas.py

## Per-file Responsibilities

- main.py: FastAPI app bootstrap, router registration, dependency wiring.
- routers/*.py: HTTP endpoints only; no business logic.
- services/*.py: orchestration and business rules.
- adapters/*.py: filesystem + subprocess + SQLite IO.
- validators/*.py: invariant evaluation and evidence generation.
- constants.py: invariant order, blocker list, config defaults.
- schemas.py: Pydantic request/response models (Layer 3 envelopes).

## Function Signature Map

### Routers

- POST /api/session/start -> session_service.start_session()
- POST /api/ops/run-sync -> session_service.run_sync()
- POST /api/ops/run-validate -> session_service.run_validate()
- GET /api/actions/next -> action_queue_service.get_next_actions(limit)
- GET /api/findings -> state_service.list_findings(filters)
- GET /api/findings/{id} -> state_service.get_finding(id)
- PATCH /api/findings/{id}/state -> state_service.update_finding_state(id, payload)
- GET /api/requirements -> state_service.list_requirements(filters)
- GET /api/health/summary -> health_service.get_summary()
- GET /api/export/status -> session_service.export_status()

### Services

- session_service.start_session() -> runs sync + validate + build action queue
- session_service.run_sync() -> process_adapter.run_sync_process()
- session_service.run_validate() -> validators.engine.run_all_validators(ctx)
- action_queue_service.build_action_queue(ctx) -> deterministic tiers
- state_service.update_finding_state(id, payload) -> enforce transitions

### Validators

- engine.run_all_validators(ctx) -> ValidatorReport
- rfc_normative.extract_normative_lines(rfc_path)
- matrix_parser.parse_core_rows(matrix_path)
- playbook_parser.parse_findings(playbook_path)
- toolchain_ok.check(ctx)
- parity.check(ctx)
- no_orphan_must.check(ctx)
- finding_integrity.check(ctx)
- backlink_consistency.check(ctx)
- blocker_pin.check(ctx)
- state_integrity.check(ctx)

## Validator-to-Module TODO Map

Each invariant must include: source docs, evidence kinds, recommended_action key, deterministic sort behavior.

- toolchain_ok
  - source: process_adapter logs
  - evidence kinds: summary, file_line (log ref)
  - recommended_action: run_sync_or_validate
- parity
  - source: rfc_normative + matrix_parser
  - evidence kinds: summary, file_line
  - recommended_action: repair_parity
- no_orphan_must
  - source: rfc_normative + matrix_parser
  - evidence kinds: id_list, file_line
  - recommended_action: map_orphans
- finding_integrity
  - source: matrix_parser
  - evidence kinds: id_list
  - recommended_action: add_findings
- backlink_consistency
  - source: matrix_parser + playbook_parser
  - evidence kinds: diff, id_list
  - recommended_action: fix_backlinks
- blocker_pin
  - source: handoff + playbook_parser
  - evidence kinds: id_list
  - recommended_action: restore_blockers
- state_integrity
  - source: sqlite_adapter + playbook_parser
  - evidence kinds: id_list
  - recommended_action: repair_state

## API Route-to-Service TODO Map

- session/start -> session_service.start_session
  - ok=true on execution
  - report.status=fail on invariant failures
- ops/run-sync -> session_service.run_sync
- ops/run-validate -> session_service.run_validate
- actions/next -> action_queue_service.get_next_actions
- findings -> state_service.list_findings
- findings/{id} -> state_service.get_finding
- findings/{id}/state -> state_service.update_finding_state
- requirements -> state_service.list_requirements
- health/summary -> health_service.get_summary
- export/status -> session_service.export_status

## Error Handling and Response Mapping

- 200: endpoint executed, ok=true, data/report present
- 400: invalid input or illegal state transition
- 404: missing finding/requirement
- 409: dependency conflict (optional)
- 500: engine or parser crash only

## Determinism Guarantees Checklist

- Invariant order is fixed (constants.py).
- Evidence sorting is stable (evidence.py).
- Action queue order is deterministic for identical inputs.
- run_id and generated_at are the only non-deterministic fields.

## Source Reference Rules (must implement)

- RFC references use RFC <section>:L<line>.
- File references use workspace_relative_path:L<line> when known.
- If line unknown, use workspace_relative_path only.

## Test Matrix and Pass Criteria

- Identical inputs yield byte-identical ValidatorReport (except run_id, timestamps).
- run-validate returns 200 + ok=true + report.status=fail for invariant failures.
- 500 only for parser/engine crash.
- state transitions rejected when illegal.
- Wave-1 blockers present and prioritized.
- Backlink consistency detects exact set diffs.
- Source-line mapping works for RFC <section>:L<line> format.
- Evidence ordering stable across repeated runs.

## Implementation Order (Phased)

1) Implement parsers (rfc_normative, matrix_parser, playbook_parser).
2) Implement invariant checks and engine.run_all_validators.
3) Implement adapters (docs_adapter, process_adapter, sqlite_adapter).
4) Implement services (session, action_queue, health, state).
5) Wire routers and envelope schema.

## Assumptions

- Canonical docs remain the source of truth.
- SQLite is the only app state store.
- Validators are non-mutating.
- Sync script is the only mutating generator.
