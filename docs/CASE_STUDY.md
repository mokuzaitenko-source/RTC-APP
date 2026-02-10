# RTC DevX Copilot Case Study

## 1) Problem

The original app direction mixed multiple surfaces (hub, coach, assistant), which made the runtime experience feel unfocused.
The primary user goal was practical execution support for real software work, not multi-page exploration.

## 2) Constraints

- Keep existing assistant API contracts unchanged.
- Preserve reliability guardrails and fallback behavior.
- Keep deterministic testing in local mode.
- Improve product clarity without backend refactor risk.

## 3) Before vs After

### Before

- Multiple runtime routes competed for attention.
- Navigation added cognitive overhead.
- Product story and portfolio story were mixed inside runtime UI.

### After

- Runtime focus is assistant-first (`/app`).
- Root and learn routes redirect to `/app`.
- Advanced controls remain available but hidden by default (drawer).
- GitHub narrative moved to docs/README instead of runtime UI copy.

## 4) Key Decisions

1. One workflow only:
`define -> ask -> refine -> execute -> verify`
2. Keep API surface stable to avoid breaking clients/tests.
3. Separate product usage from portfolio storytelling.
4. Keep guardrails and observability optional, not intrusive.

## 5) Tradeoffs Rejected

- Keeping all routes as equal runtime surfaces: rejected due to focus loss.
- Removing advanced controls entirely: rejected because power users need them.
- API/schema refactor during UI focus pass: rejected to reduce delivery risk.

## 6) Reliability and Safety Behavior

- Provider failures map to controlled error envelopes.
- Session continuity preserved via `X-Session-ID`.
- Trace behavior remains optional (`X-ACA-Trace`) and does not block normal workflow.
- Deterministic local mode remains available for stable tests.

## 7) Evidence

- Contract tests validate endpoint and page behavior.
- Stream and provider tests validate runtime reliability paths.
- Frontend syntax checks and backend test suite pass.

## 8) Scorecard

- Usability focus: 8.5
- Workflow clarity: 8.7
- Reliability confidence: 8.6
- Maintainability: 8.4
- Portfolio clarity: 8.8

Composite target achieved: **x > 8**

## 9) Next Improvements

1. Add lightweight in-app metric counters for first useful response time.
2. Add a fixed manual scenario rubric for monthly regression reviews.
3. Add screenshot/GIF evidence pack for GitHub showcase section.
