# ACA v4 Master Rulebook (Runtime Edition)

## Scope
This rulebook defines runtime behavior for the assistant ACA pipeline in this repository.

## Core Rules
1. Safety-first precedence: Tier 0 safety modules override all downstream decisions.
2. Deterministic module order: M0-M23 executes in fixed sequence.
3. Contract stability: API payload shape remains backward compatible.
4. Traceability: Each module emits a trace event when tracing is enabled.
5. Memory policy: Session text memory is in-memory only and sanitized before storage.
6. Fallback policy: Controlled safe fallback responses are preferred over hard failures.

## Module Coverage In This Release
- Fully implemented: M0-M23

## API Contract Versions
- `v1` compatibility endpoints:
  - `POST /api/assistant/respond`
  - `POST /api/assistant/stream`
- `v2` versioned endpoints:
  - `POST /api/assistant/respond-v2`
  - `POST /api/assistant/stream-v2`

### v2 SSE Event Sequence
1. `meta`
2. `trace` (optional)
3. `checkpoint`
4. `delta`
5. `done`
6. `error`

