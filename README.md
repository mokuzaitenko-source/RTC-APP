# RTC-APP (Oversight Assistant)

Assistant-first web app built with FastAPI + vanilla JS.  
It delivers streamed responses, session-aware memory, model selection, and deterministic fallback behavior for reliable planning workflows.

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
- Implemented contract/unit/integration tests for stream event sequencing, model allowlist enforcement, and compatibility paths (`30` tests passing).

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

## Environment Variables

Copy `.env.example` and set values:

- `ASSISTANT_PROVIDER_MODE` (`auto`, `openai`, `local`)
- `OPENAI_API_KEY` (required for OpenAI mode)
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

## Tests

```bash
node --check app/frontend/app.js
python -m unittest
python -m pytest -q
```

## GitHub Launch Pack

For repo description, topics, and a longer interview pitch, use:
`docs/GITHUB_LAUNCH_PACK.md`
