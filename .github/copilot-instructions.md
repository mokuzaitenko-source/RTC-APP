# Copilot Instructions

## Product Goal
- Build and maintain a local-first governance executor for oversight workflows.
- Keep behavior deterministic: same inputs -> same invariant order, evidence order, and action queue.
- Canonical truth is markdown docs + sync script output; SQLite is state overlay only.

## Core Repo Map
- `app/backend/`: FastAPI app (routers, services, adapters, validators).
- `tests/fixtures/validators/`: deterministic fixtures and golden outputs (`v00`-`v08`).
- `docs/specs/`: Layer 2/3 contracts and fixture spec.
- `scripts/sync_oversight_trace.py`: mutating sync command for RFC/matrix/playbook/handoff.

## Runtime Contracts You Must Preserve
- Invariant order is fixed:
  - `toolchain_ok`, `parity`, `no_orphan_must`, `finding_integrity`, `backlink_consistency`, `blocker_pin`, `state_integrity`
- API envelope:
  - `ok`, `generated_at`, optional `request_id`, optional `run_event|report|data|error`
- Validation semantics:
  - Endpoint execution success may still return `report.status="fail"` for invariant failures.
- Source references:
  - `RFC <section>:L<line>` and workspace-relative `path:L<line>`.

## Build and Verify Workflow
- Lint: `ruff check app tests`
- Types: `mypy app tests`
- Tests: `python -m unittest discover -s tests`
- App run: `python -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000`

## Prompting-Book Build Heuristics (from `C:\Users\alvin\Desktop\propmting book.txt`)
- Use this loop for implementation tasks:
  - `Instruct -> Decompose -> Verify -> Iterate`
- For risky changes, apply:
  - `Verify-step-by-step` and explicit confidence limits (do not guess parser/schema behavior).
- For ambiguous tasks, apply:
  - `Self-ask` sub-questions internally, then implement smallest deterministic slice first.
- For accuracy/freshness-sensitive behavior, apply:
  - retrieval and source-linking discipline (never invent refs, preserve line-anchored evidence).
- For safety/constraints, apply:
  - strict enums/literals at request boundaries, no silent coercion.

## Project-Specific Conventions
- Do not add a `done` finding state; completion is derived from invariants.
- Keep `run_validate` non-mutating; only sync script mutates canonical docs.
- Keep error messages UI-safe (one sentence), with detail in `evidence`.
- When adding a validator, add/extend fixture coverage and golden expected JSON.
