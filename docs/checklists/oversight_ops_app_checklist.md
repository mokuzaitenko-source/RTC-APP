# Oversight Ops App Checklist (Architecture + Prompting)

Use this checklist as the working operator/build gate for the local oversight app.

## A. Architecture Kernel (from Unified Cognitive Architecture Overview)

- [x] Oversight is treated as a first-class kernel, not a post-output wrapper.
- [x] Runtime pipeline is staged and gated (sync/validate/action queue sequence).
- [x] Deterministic validator order is fixed and enforced.
- [x] Safety/quality arbitration is explicit and visible via API outputs.
- [x] Canonical truth stays in docs (`RFC`, trace matrix, playbook, handoff).
- [ ] Add explicit policy card rendering in UI for all locked thresholds.
- [ ] Add visible invariant lock indicator in operator UI (locked/unlocked).

## B. Deterministic Operations Flow

- [x] `POST /api/session/start` runs sync + validate and returns top actions.
- [x] `POST /api/ops/run-validate` returns deterministic invariant output.
- [x] `GET /api/actions/next` returns deterministic ranked action cards.
- [x] Toolchain hard-fail path short-circuits to remediation-only actions.
- [x] Wave-1 blockers are ranked before other work.
- [x] Ready-for-validation gate is ranked before invariant repair.
- [x] Every generated action card includes at least one command and one file link.
- [ ] Add route-level contract tests for all endpoints (200/400/404/422/500 envelopes).

## C. Prompting/Reasoning Guardrails (from `propmting book.txt`)

- [x] Verification-first behavior exists (invariants + fixture goldens).
- [x] Iteration loop exists (sync -> validate -> action queue).
- [x] Retrieval/tool-path is represented in architecture docs and trace model.
- [ ] Add explicit confidence calibration field in operator-facing outputs.
- [ ] Add an assumption-disclosure card when confidence/risk triggers fire.
- [ ] Add a lightweight chain-of-verification export section in `/api/export/status`.

## D. UI Operator Loop (v1 minimal)

- [x] Local control-room UI is mounted at `/app`.
- [x] UI can run session, sync, validate, and refresh action/health panels.
- [x] UI shows top actions, health badges, and run log timeline.
- [ ] Add blocker detail pane (dependencies, impacted req IDs, proof expectations).
- [ ] Add requirement drilldown panel with source link jump actions.
- [ ] Add status export panel with copy-to-clipboard behavior.

## E. Release Gate Before “User-Ready”

- [x] `ruff` passes.
- [x] `mypy` passes.
- [x] Unit tests pass (validators + API contracts + action queue tests).
- [ ] UX pass: complete one blocker workflow without dead-end navigation.
- [ ] Observability pass: include run IDs and per-action trace correlation in UI.

## F. Immediate Next Sprint (recommended order)

1. Add blocker detail pane + proof expectation schema rendering.
2. Add full API envelope contract tests for validation and error routes.
3. Add requirement drilldown + source links from action cards.
4. Add observability layer (trace IDs across run events and action cards).
