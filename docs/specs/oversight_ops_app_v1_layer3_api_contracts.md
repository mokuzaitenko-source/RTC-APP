# Layer 3 API Contracts (Local Oversight App v1)

## Goal

Lock request/response/error contracts for all v1 endpoints, aligned to the validator spec and Layer 2 read models. Contracts must be deterministic and UI-safe.

Related specs:

- docs/specs/oversight_ops_app_v1_layer2.md
- docs/specs/oversight_ops_app_v1_layer2_validators.md

## Cross-Cutting Rules

- All responses are JSON.
- All timestamps are ISO 8601.
- Invariant failures return 200 with ok=true and report.status=fail; 500 only for engine or parser crash.
- Error messages are one sentence; stack traces must never appear in message fields.
- Ordering of invariants[] is fixed (see validator spec).
- Ordering of evidence[] is deterministic (sorted).
- Action queue ordering is deterministic for identical inputs.
- run_id and generated_at are the only non-deterministic fields.

## Common Response Envelope

All endpoints return the same envelope shape.

```
{
  "ok": true,
  "generated_at": "iso8601",
  "run_event": RunEvent,
  "report": ValidatorReport,
  "data": {},
  "error": {
    "code": "string",
    "message": "string",
    "evidence": ["string"]
  }
}
```

Envelope rules:

- ok=true when the endpoint executes successfully, even if invariants fail.
- ok=false only when an error occurs or execution fails.
- run_event/report/data are optional and may be omitted when not applicable.
- error is omitted on success.

## Canonical Types (API)

### EvidenceItem

```
{
  "kind": "file_line | id_list | summary | diff",
  "ref": "string",
  "detail": "string",
  "hash": "string | null"
}
```

### InvariantResult

```
{
  "id": "string",
  "status": "pass | fail",
  "message": "string",
  "evidence": [EvidenceItem],
  "recommended_action": "string",
  "suggested_matches": [
    {"rfc_line_id": "string", "suggested_req_ids": ["string"]}
  ]
}
```

### ValidatorReport

```
{
  "run_id": "string",
  "run_type": "validate",
  "status": "pass | fail",
  "started_at": "iso8601",
  "ended_at": "iso8601",
  "invariants": [InvariantResult],
  "summary": "string"
}
```

### RunEvent

```
{
  "run_id": "string",
  "run_type": "sync | validate | session_start",
  "status": "pass | fail",
  "started_at": "iso8601",
  "ended_at": "iso8601",
  "stdout": "string",
  "stderr": "string",
  "summary": "string"
}
```

### ActionCard

```
{
  "action_id": "string",
  "tier": 0,
  "type": "resolve_blocker | run_sync | run_validate | repair_invariant | triage_section | export_status",
  "target": "string",
  "title": "string",
  "why_now": "string",
  "steps": ["string"],
  "commands": ["string"],
  "links": ["string"]
}
```

### FindingReadModel

```
{
  "finding_id": "string",
  "is_wave1_blocker": true,
  "dependencies": ["string"],
  "impacted_req_ids": ["string"],
  "impact_count": 0,
  "app_status": "unstarted | in_progress | blocked | ready_for_validation",
  "proof_expectations": ["string"],
  "source_refs": ["string"]
}
```

### RequirementReadModel

```
{
  "req_id": "string",
  "status": "covered | partial | gap",
  "normative_level": "MUST | SHALL | SHOULD | MAY",
  "enforcement_tbd": true,
  "proof_tbd": true,
  "linked_findings": ["string"],
  "source_ref": "string"
}
```

### FindingState

```
{
  "finding_id": "string",
  "status": "unstarted | in_progress | blocked | ready_for_validation",
  "note": "string | null",
  "updated_at": "iso8601"
}
```

## Source Reference Format (v1)

- Source references must support RFC source-line mode.
- RFC references use: RFC <section>:L<line> (example: RFC 4.1:L118).
- File references use workspace-relative path:L<line> when known.
- If line is unknown, use workspace-relative path only.
- Evidence items with kind=file_line MUST use the file reference format above.

## Orphan Mapping Mode (API Contract)

- orphan_mapping_mode=source_line is the v1 default.
- In source_line mode, no_orphan_must uses RFC <section>:L<line> mappings.
- In hybrid migration, the validator MAY populate suggested_matches but MUST NOT change pass/fail criteria.
- In req_tag_strict mode, suggested_matches MUST be omitted unless tags exist.

## Endpoints

### POST /api/session/start

Runs sync then validate, computes action queue.

Response:

```
{
  "ok": true,
  "generated_at": "iso8601",
  "data": {
    "run_events": [RunEvent],
    "invariants": [InvariantResult],
    "top_actions": [ActionCard]
  }
}
```

### POST /api/ops/run-sync

Executes sync_oversight_trace.py.

Response:

```
{
  "ok": true,
  "generated_at": "iso8601",
  "run_event": RunEvent
}
```

### POST /api/ops/run-validate

Runs validator engine only (non-mutating).

Response:

```
{
  "ok": true,
  "generated_at": "iso8601",
  "report": ValidatorReport
}
```

### GET /api/health/summary

Returns parity, coverage, blockers, findings footprint.

Response:

```
{
  "ok": true,
  "generated_at": "iso8601",
  "data": {
    "parity": {"rfc_normative_count": 0, "matrix_core_count": 0, "status": "pass | fail"},
    "coverage": {"covered": 0, "partial": 0, "gap": 0},
    "blockers": {"wave1": ["F-001"], "unresolved": ["F-001"]},
    "findings": {"total": 0, "by_wave": {"1": 0, "2": 0}, "by_severity": {"CRITICAL": 0}}
  }
}
```

### GET /api/actions/next?limit=10

Returns deterministic queue sorted by tier and tie-breakers.

Response:

```
{
  "ok": true,
  "generated_at": "iso8601",
  "data": {"actions": [ActionCard]}
}
```

### GET /api/findings

Query by finding_id, wave, is_blocker, status.

Response:

```
{
  "ok": true,
  "generated_at": "iso8601",
  "data": {"findings": [FindingReadModel]}
}
```

### GET /api/findings/{id}

Returns dependencies, impacted reqs, app state, proof expectations.

Response:

```
{
  "ok": true,
  "generated_at": "iso8601",
  "data": {"finding": FindingReadModel}
}
```

### PATCH /api/findings/{id}/state

Allowed transitions only among the four states; no "done".

Request:

```
{
  "status": "unstarted | in_progress | blocked | ready_for_validation",
  "note": "string | null"
}
```

Response:

```
{
  "ok": true,
  "generated_at": "iso8601",
  "data": {"state": FindingState}
}
```

### GET /api/requirements

Query by req_id, status, finding, section.

Response:

```
{
  "ok": true,
  "generated_at": "iso8601",
  "data": {"requirements": [RequirementReadModel]}
}
```

### GET /api/export/status

Returns shareable markdown status.

Response:

```
{
  "ok": true,
  "generated_at": "iso8601",
  "data": {"markdown": "string"}
}
```

## Status Codes

- 200: endpoint ran and returned a result (even if invariants fail)
- 400: invalid input or illegal state transition
- 404: missing finding/requirement
- 409: conflict with current state (optional, dependency-based)
- 500: parser or engine crash only
