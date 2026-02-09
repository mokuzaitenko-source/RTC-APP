# Module 18: Task Integrity

## Purpose
Enforce acceptance completeness before output can proceed to coherence/fallback handling.

## Inputs
- Candidate output payload from `M17` (`mode`, `plan`, `candidate_response`, `notes`).
- Active request controls (`risk_tolerance`, `max_questions`).

## Outputs
- Integrity verdict (`pass` + `failures[]`).
- Updated `state.meta_policy.integrity_fail` flag when checks fail.
- Trace event with `status=pass|blocked`.

## Process / Pseudocode
```text
failures = []
if mode not in {clarify, plan_execute}: failures += invalid_mode
if candidate_response empty: failures += missing_candidate_response
if mode == plan_execute:
  require plan length >= 4
  require acceptance/verify/check token in at least one step
  require fallback token in at least one step
if failures:
  set integrity_fail flag
  append integrity markers to notes
emit module output and trace
```

## Safety Checks
- Never bypass Tier-0 safety state.
- Integrity failure routes downstream to deterministic fallback manager.

## Failure Modes
- `invalid_mode`
- `missing_candidate_response`
- `insufficient_plan_depth`
- `missing_acceptance_check`
- `missing_fallback_step`

## Upstream / Downstream
- Upstream: `M17`
- Downstream: `M19`
