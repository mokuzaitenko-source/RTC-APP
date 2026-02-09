# GitHub Launch Pack: RTC-APP

## Repo Name

`RTC-APP`

## Public Repo Description (short)

Assistant-first FastAPI app with SSE streaming, session memory, model picker, and deterministic test mode.

## README Tagline (one-liner)

Full-stack AI assistant app with real-time responses, backend memory, and production-style API contracts.

## Suggested Topics

`fastapi`, `python`, `javascript`, `sse`, `openai-api`, `llm`, `full-stack`, `chatbot`, `ai-assistant`, `testing`

## Recruiter Pitch (60 seconds)

RTC-APP is an assistant-first web product that demonstrates practical LLM engineering patterns.  
It includes streaming responses over SSE, session-aware memory on the server, model selection with backend allowlisting, and deterministic local behavior for repeatable tests.  
The API remains backward-compatible through a non-stream endpoint while introducing a dedicated stream path for richer UX.

## Resume Bullets

- Built a full-stack assistant application with FastAPI and vanilla JavaScript, adding SSE streaming, model selection, and server-side session memory.
- Implemented provider abstraction with deterministic local mode and OpenAI mode, including safe error handling and compatibility-preserving API design.
- Added test coverage for stream event order, invalid model validation, missing-key behavior, and endpoint contracts (`30` tests passing).

## Project Story For Interviews

### Problem
Most assistant demos are shallow and non-deterministic, making them hard to test and hard to trust in development workflows.

### Approach
Separated provider logic from API routes, introduced session memory boundaries (TTL + max turns), and exposed model policy from backend to frontend.

### Result
Delivered a responsive assistant UX with controlled failure modes and reliable regression testing, while keeping legacy client compatibility.

## Portfolio Caption

Designed and shipped an assistant-first full-stack app with streaming AI responses, session memory, and production-ready API contracts.
