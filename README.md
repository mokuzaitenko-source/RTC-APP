# RTC DevX Copilot

Assistant-first platform focused on one real workflow:  
`define problem -> generate plan -> implement -> verify -> refine`

Default output contract for actionable responses:
- `3` next actions
- `1` verification step
- `1` fallback step

## Case Study Summary

### Problem
Most assistant UIs are broad but not practical for daily engineering execution.  
The goal here was to build something usable every day for real build/debug loops, not a demo chat screen.

### Solution
RTC DevX Copilot ships a single runtime surface (`/app`) with:
- streaming assistant responses (SSE)
- session continuity across refreshes
- strict `3+1+1` execution outputs for build/debug prompts
- model/risk/API/trace controls hidden in one advanced drawer
- deterministic safety/fallback behavior
- v1/v2 contract-compatible APIs

### Architecture Choices
- FastAPI backend with provider abstraction (`local`, `openai`, `auto`)
- server-side in-memory session service with sanitization and limits
- assistant orchestration path with ACA-governed checks
- assistant-only frontend runtime to reduce navigation noise

### Proof and Quality Signals
- API contract tests for v1/v2 endpoints
- stream sequencing and error-path coverage
- deterministic local mode for stable regression checks
- full test suite in CI-style local commands (`unittest`, `pytest`, `node --check`)

### Outcomes
- clearer product focus (assistant-only runtime path)
- faster first useful response UX
- reduced UI clutter while preserving power controls in advanced drawer
- repository narrative aligned for GitHub/job showcase

## Runtime Scope

- Runtime product surface: `/app` only
- `GET /` redirects to `/app`
- `GET /learn` redirects to `/app`
- Archived showcase assets are kept in `docs/showcase/frontend_archive/`

## Recruiter Snapshot

RTC DevX Copilot is a full-stack AI product implementation, not just UI polish.
It demonstrates production-minded API contracts, streaming transport, memory discipline, fallback safety, and iterative product simplification.

## Resume Bullets (Copy/Paste Ready)

- Built an assistant-first FastAPI platform that streams responses (SSE), preserves session context, and supports model/risk controls for practical software workflows.
- Implemented provider abstraction (local deterministic + OpenAI) with controlled error envelopes, timeout handling, and compatibility-preserving v1/v2 APIs.
- Improved product focus by reducing runtime surface to one assistant workflow, while documenting architecture and evidence as a GitHub case study.

## Case Study Document

See `docs/CASE_STUDY.md` for before/after decisions, rejected tradeoffs, reliability behavior, and lessons learned.

## Run Locally

```bash
pip install -r requirements.txt
uvicorn app.backend.main:app --reload
```

Open: `http://127.0.0.1:8000/app`

One-command launcher (Windows):

```powershell
.\start_app.ps1
```

## API Surface

### `POST /api/assistant/respond`
Non-streaming JSON response (compatibility path).

### `POST /api/assistant/stream`
SSE stream (`text/event-stream`) with events:
- `meta`
- `delta`
- `done`
- `error`

### `POST /api/assistant/respond-v2`
Versioned breaking schema response:
- `aca_version`
- `session_id`
- `mode`
- `final_message`
- `decision_graph`
- `module_outputs` (`M10..M23`)
- `quality`
- `safety`
- `fallback`
- optional `trace`

### `POST /api/assistant/stream-v2`
SSE stream (`text/event-stream`) with events:
- `meta`
- `trace` (optional)
- `checkpoint`
- `delta`
- `done`
- `error`

### `GET /api/assistant/models`
Returns:
- `models`
- `default_model`
- `provider_mode`
- `effective_provider_mode`
- `provider_ready`
- `provider_warnings`

## Session Handling

Assistant endpoints accept `X-Session-ID`.

- Frontend sends this header each request.
- Backend generates a fallback ID if header is missing.
- Session context is reused server-side for follow-up turns.
- Session text is sanitized before in-memory storage.

Optional trace header:

- `X-ACA-Trace: 1`
- `/respond` includes `data.aca_trace`
- `/stream` emits `trace` events and includes `done.data.aca_trace`
- `/respond-v2` includes `data.trace` (or request `trace=true`)
- `/stream-v2` emits `trace` and `checkpoint` events and includes `done.data.trace`

## Environment Variables

Copy `.env.example` and set values:

- `ASSISTANT_PROVIDER_MODE` (`local`, `auto`, `openai`)  
  Recommended default for daily use: `local`
- `ASSISTANT_ACA_ENABLED` (`1`, `0`)
- `OPENAI_API_KEY` (required for `openai`; optional for `auto`)
- `ASSISTANT_OPENAI_MODEL`
- `ASSISTANT_OPENAI_MODELS` (comma-separated allowlist)
- `ASSISTANT_OPENAI_TIMEOUT_S`
- `ASSISTANT_SESSION_TTL_S`
- `ASSISTANT_SESSION_MAX_TURNS`
- `ASSISTANT_SESSION_CONTEXT_TURNS`
- `AUTOLOOP_MODEL`
- `AUTOLOOP_TARGET_X`
- `AUTOLOOP_MAX_CYCLES`
- `AUTOLOOP_MAX_MINUTES`
- `AUTOLOOP_AUTOCOMMIT`
- `AUTOLOOP_LOCK_GATE`
- `AUTOLOOP_PROFILE` (`strict`, `compat`) default `strict`
- `AUTOLOOP_DEV_STACK_V2` (deprecated compatibility flag)
- `AUTOLOOP_UPGRADE_TARGET` default `10`
- `AUTOLOOP_DEV3_MODE` (`local`, `cloud`, `hybrid`) default `local`
- `AUTOLOOP_DEV4_POLICY` (`strict`, `balanced`)
- `AUTOLOOP_RESEARCH_POLICY` (`primary_docs`, `broad_web`, `local_only`)
- `AUTOLOOP_DEV7_BLOCK_ON_SAFETY` (`1`, `0`)
- `AUTOLOOP_DEV8_REQUIRE_RELEASE_PASS` (`1`, `0`)
- `AUTOLOOP_MAX_REVISION_ATTEMPTS`
- `AUTOLOOP_DEBUG_PACK` (`standard`, `extended`)

## Provider Errors

- `assistant_provider_unconfigured` -> `503`
- `assistant_provider_timeout` -> `504`
- `assistant_provider_error` -> `502`
- `assistant_invalid_model` -> `400`

`auto` provider mode behavior:
- If `OPENAI_API_KEY` is present, the app uses OpenAI.
- If key is missing, runtime falls back to deterministic local mode.

## Tests

```bash
node --check app/frontend/app.js
python -m unittest
python -m pytest -q
```

## One-Command Automation Gate

Run the full quality gate (checks + 8 smoke scenarios + 8-worker stress burst):

```powershell
.\scripts\run_airtight_gate.ps1
```

Or from Command Prompt:

```bat
run_quality_gate.bat
```

Generated reports:

- `output/quality/airtight_smoke_report.json`
- `output/quality/airtight_smoke_report.md`

Useful flags:

```powershell
.\scripts\run_airtight_gate.ps1 -SkipChecks
.\scripts\run_airtight_gate.ps1 -SkipStress
```

## Prompt-Book Auto-Improvement Loop

Run the autonomous prompt-book loop:

```powershell
.\scripts\run_prompt_book_loop.ps1
```

Or from Command Prompt:

```bat
run_prompt_book_loop.bat
```

What it does each cycle:

- Reads one technique from `docs/prompting_book.md`
- Generates a proposal via Dev3 strategy:
  - local-first by default (no key required)
  - optional cloud/hybrid model-backed generation
- Applies edits with locked-file policy
- Runs `node --check`, `unittest`, `pytest`
- Runs `scripts/run_airtight_gate.py`
- Computes:
  - `x_gate_100` from gate `overall_x * 10`
  - `x_composite_100 = 0.35*workflow + 0.25*reliability + 0.15*ux + 0.15*safety + 0.10*release`
- Auto-commits locally only on accepted upgrades with green checks

Note:

- In `local` mode, no API key is required.
- In `cloud` mode, `OPENAI_API_KEY` is required.
- `--dev-stack-v2` is deprecated and maps to `--profile strict`.

Stop condition:

- `accepted_upgrades_total >= upgrade_target`
- `x_gate_100 == target_x`
- `x_composite_100 == target_x`
- current cycle checks are fully green

Generated artifacts:

- `output/quality/prompt_book_loop.jsonl`
- `output/quality/prompt_book_loop_summary.json`
- `output/quality/prompt_book_loop_summary.md`

Useful flags:

```powershell
.\scripts\run_prompt_book_loop.ps1 -DryRun -MaxCycles 2
.\scripts\run_prompt_book_loop.ps1 -TargetX 100 -MaxCycles 12 -MaxMinutes 180
.\scripts\run_prompt_book_loop.ps1 -Profile strict -UpgradeTarget 10 -Dev3Mode local
.\scripts\run_prompt_book_loop.ps1 -Profile compat -Dev3Mode local
```

## ACA Docs-as-Code

Canonical docs are stored in:

- `docs/aca_v4/master_rulebook.md`
- `docs/aca_v4/glossary.md`
- `docs/aca_v4/modules/module_00_*.md ... module_23_*.md`
- `docs/prompting_book.md`

Build PDF docs:

```bash
python scripts/build_aca_docs.py
python scripts/package_aca_docs.py
```

## GitHub Launch Pack

For repo description, topics, and a longer interview pitch, use:
`docs/GITHUB_LAUNCH_PACK.md`
