# Layer 2 Validator Fixtures Spec (Golden JSON + Real Fixture Paths)

## Summary

This spec defines deterministic validator fixtures and golden outputs for v1. It locks fixture directory layout, naming, canonicalization rules, and expected `run-validate` payload assertions so implementation can proceed without interpretation gaps.

Related specs:

- `docs/specs/oversight_ops_app_v1_layer2.md`
- `docs/specs/oversight_ops_app_v1_layer2_validators.md`
- `docs/specs/oversight_ops_app_v1_layer3_api_contracts.md`

## Scope

- Define fixture directory layout under `tests/fixtures/validators/`.
- Define fixture naming, required files, and golden output contracts.
- Define canonicalization for non-deterministic fields.
- Cover all invariants, deterministic evidence ordering, and orphan mapping modes.
- Define one integration smoke fixture policy against current repo docs.

Out of scope:

- Validator implementation code.
- API router implementation.
- UI fixture visualization.

## Interface Alignment (Locked)

1. Contracts must align with Layer 2 validator and Layer 3 API specs.
2. `run-validate` envelope semantics:

- HTTP `200` when endpoint executes.
- `ok=true` when endpoint execution succeeds.
- `report.status=fail` when invariant failures exist.
- `500` only for parser/engine crash.

1. Golden output payloads must use canonical Layer 3 envelope and Layer 2 validator types.

## Fixture Directory Layout

For each fixture ID:

`tests/fixtures/validators/<fixture_id>/`

Required files:

- `rfc.md`
- `matrix.md`
- `playbook.md`
- `handoff.md`
- `state_seed.json`
- `expected.run_validate.json`

Optional:

- `notes.md` (human rationale only; never used for assertion comparisons)

## Fixture Naming Convention

- Prefix: `vNN_` where `NN` is two-digit stable order.
- Use lowercase snake-style suffix describing target behavior.
- Fixture IDs are immutable once referenced by tests.

## Golden Comparison Canonicalization

Before comparing response to `expected.run_validate.json`, normalize:

- `run_id` -> `"<RUN_ID>"`
- `generated_at` -> `"<TS>"`
- `started_at` -> `"<TS>"`
- `ended_at` -> `"<TS>"`

Rules:

1. Compare full JSON post-normalization (no partial fuzzy checks).
2. Preserve order-sensitive arrays exactly:

- `report.invariants[]` fixed order from validator spec.
- `evidence[]` sorted by validator evidence rules.

1. Message strings must match templates exactly.
1. No stack traces may appear in `message`.

## Source Reference Contract in Fixtures

- RFC source references use `RFC <section>:L<line>`.
- File references use `workspace_relative_path:L<line>` when line known.
- Fallback to `workspace_relative_path` when line unknown.
- Evidence entries with line references must use the same canonical format.

## Required Fixture Matrix (Minimum Set)

| Fixture ID | Target Invariant(s) | Expected Failing Invariant IDs | Expected report.status | Required Evidence Kinds | Required recommended_action Key(s) |
| --- | --- | --- | --- | --- | --- |
| `v00_all_pass_source_line` | all | none | `pass` | summary | n/a |
| `v01_toolchain_fail_sync` | toolchain_ok | `toolchain_ok` | `fail` | summary, file_line | `run_sync_or_validate` |
| `v02_parity_off_by_one` | parity | `parity` | `fail` | summary, file_line | `repair_parity` |
| `v03_orphan_must_source_line` | no_orphan_must | `no_orphan_must` | `fail` | id_list, file_line | `map_orphans` |
| `v04_finding_integrity_gap_without_finding` | finding_integrity | `finding_integrity` | `fail` | id_list | `add_findings` |
| `v05_backlink_set_diff` | backlink_consistency | `backlink_consistency` | `fail` | diff, id_list | `fix_backlinks` |
| `v06_blocker_pin_missing_blocker` | blocker_pin | `blocker_pin` | `fail` | id_list | `restore_blockers` |
| `v07_state_integrity_unknown_finding` | state_integrity | `state_integrity` | `fail` | id_list | `repair_state` |
| `v08_state_integrity_invalid_status` | state_integrity | `state_integrity` | `fail` | id_list | `repair_state` |
| `v09_orphan_req_tag_strict_missing_tags` | no_orphan_must (`req_tag_strict`) | `no_orphan_must` | `fail` | id_list, file_line | `map_orphans` |
| `v10_orphan_hybrid_suggested_matches` | no_orphan_must (`hybrid`) | `no_orphan_must` | `fail` | id_list, file_line | `map_orphans` |
| `v11_evidence_sort_stability` | evidence ordering contract | invariant depends on fixture setup | `pass` or `fail` per setup | deterministic sorted output (all applicable kinds) | action key depends on setup |

## Per-Fixture Required Assertions

For every fixture:

1. `ok=true` for successful validator execution.
2. `report.status` matches expected pass/fail.
3. `report.invariants[]` returned in fixed canonical order.
4. Failed invariants include:

- one-sentence `message`
- deterministic `evidence` ordering
- expected `recommended_action`.

1. `error` omitted for successful execution responses.

## Orphan Mapping Mode Coverage

### `source_line` (v1 default)

- Authoritative pass/fail mode for v1.
- Uses line-source mapping (`RFC <section>:L<line>`).

### `hybrid` (migration mode)

- May add `suggested_matches`.
- Must not change pass/fail criteria from authoritative source-line decision basis.

### `req_tag_strict` (future strict mode)

- Requires REQ-tag mapping.
- Fixtures must explicitly fail when tags are absent or unmapped.

## Integration Fixture Policy (Non-Golden)

Add one integration smoke fixture against current repo docs:

- ID: `integration_current_repo_smoke`
- Purpose: verify engine execution and invariant shape against live docs.
- Assertion policy: schema + invariant IDs + ordering only.
- Do not use exact golden payload comparison (docs are expected to evolve).

## Expected JSON Template Contract

Each `expected.run_validate.json` must follow:

```json
{
  "ok": true,
  "generated_at": "<TS>",
  "report": {
    "run_id": "<RUN_ID>",
    "run_type": "validate",
    "status": "pass | fail",
    "started_at": "<TS>",
    "ended_at": "<TS>",
    "invariants": [],
    "summary": "string"
  }
}
```

## Implementation Notes

- Prefer text fixtures (`state_seed.json`) over binary sqlite fixture files.
- Keep fixture content synthetic and stable.
- Keep fixture IDs and expected action keys stable once released.

## Cross-Doc Pointer Requirements

1. Layer 2 validator spec must include:

- `Related fixture spec: docs/specs/oversight_ops_app_v1_layer2_validator_fixtures.md`

1. `SESSION_HANDOFF.md` must include a pointer to this fixture spec.

## Assumptions and Defaults

- No `app/backend` runtime code exists yet; this spec defines future test assets.
- Canonical docs remain source of truth for runtime behavior.
- Golden fixtures remain synthetic to avoid churn from live doc edits.
