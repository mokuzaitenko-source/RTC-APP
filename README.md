# RTC-APP (Oversight Assistant)

Assistant-first web app built with FastAPI + vanilla JS.  
It delivers streamed responses, session-aware memory, model selection, and deterministic fallback behavior for reliable planning workflows.

## ACA Fusion Runtime

The assistant now runs through an internal ACA orchestrator pipeline (`M0-M23`) with:

- Implemented modules: `M0-M23` (including deterministic `M18-M20`)
- Tiered authority precedence (`tier0_safety -> tier1_meta -> tier2_bottleneck -> tier3_operational`)
- Feature flag switch:
  - `ASSISTANT_ACA_ENABLED=1` (default)
  - `ASSISTANT_ACA_ENABLED=0` (legacy path)

## Why This Project Is Strong

- Real-time assistant UX using Server-Sent Events (SSE).
- Server-side session memory (TTL + turn limits).
- Backend model allowlist and model picker.
- Backward-compatible non-stream endpoint for clients/tests.
- Deterministic local mode for stable test automation.

## Recruiter Snapshot

RTC-APP is a full-stack AI product implementation, not just a chat UI.  
It includes API contracts, provider abstraction, streaming transport, memory controls, validation tests, and documentation.

## Resume Bullets (Copy/Paste Ready)

- Built an assistant-first FastAPI web app with SSE streaming, server-side session memory, and model selection, preserving backward API compatibility.
- Designed a provider abstraction supporting local deterministic mode and OpenAI Responses API mode with controlled error envelopes and timeout handling.
- Implemented contract/unit/integration tests for stream event sequencing, model allowlist enforcement, and compatibility paths (`54` tests passing).

## Run Locally

```bash
pip install -r requirements.txt
uvicorn app.backend.main:app --reload
```

Open: `http://127.0.0.1:8000/app`

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

- `ASSISTANT_PROVIDER_MODE` (`auto`, `openai`, `local`)
- `ASSISTANT_ACA_ENABLED` (`1`, `0`)
- `OPENAI_API_KEY` (required for `openai`; optional for `auto`)
- `ASSISTANT_OPENAI_MODEL`
- `ASSISTANT_OPENAI_MODELS` (comma-separated allowlist)
- `ASSISTANT_OPENAI_TIMEOUT_S`
- `ASSISTANT_SESSION_TTL_S`
- `ASSISTANT_SESSION_MAX_TURNS`
- `ASSISTANT_SESSION_CONTEXT_TURNS`

## Provider Errors

- `assistant_provider_unconfigured` -> `503`
- `assistant_provider_timeout` -> `504`
- `assistant_provider_error` -> `502`
- `assistant_invalid_model` -> `400`

`auto` provider mode behavior:
- If `OPENAI_API_KEY` is present, the app uses OpenAI.
- If key is missing, the app falls back to deterministic local mode.

## Tests

```bash
node --check app/frontend/app.js
python -m unittest
python -m pytest -q
```

## ACA Docs-as-Code

Canonical docs are stored in:

- `docs/aca_v4/master_rulebook.md`
- `docs/aca_v4/glossary.md`
- `docs/aca_v4/modules/module_00_*.md ... module_23_*.md`

Build PDF docs:

```bash
python scripts/build_aca_docs.py
python scripts/package_aca_docs.py
```

## GitHub Launch Pack

For repo description, topics, and a longer interview pitch, use:
`docs/GITHUB_LAUNCH_PACK.md`
