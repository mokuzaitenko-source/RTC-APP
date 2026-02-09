# Module 19: Error and Coherence Checker

## Purpose
Classify coherence and quality failures that require fallback intervention.

## Inputs
- Post-integrity payload from `M18`.
- `state.quality_score` and upstream integrity flags.

## Outputs
- Coherence verdict (`pass` + `issues[]`).
- `state.meta_policy.coherence_fail` flag on failure.
- Trace event with `status=pass|blocked`.

## Process / Pseudocode
```text
issues = []
if candidate has contradictory imperative language: issues += contradictory_instruction_language
if weighted quality < threshold: issues += low_weighted_quality
if integrity fail set: issues += upstream_integrity_failure
if plan_execute and plan empty: issues += missing_plan_after_refinement
if issues:
  set coherence_fail flag
emit module output and trace
```

## Safety Checks
- Coherence verdict never overrides Tier-0 safety blocks.
- Coherence failures are routed to `M20` fallback selection.

## Failure Modes
- `contradictory_instruction_language`
- `low_weighted_quality`
- `upstream_integrity_failure`
- `missing_plan_after_refinement`

## Upstream / Downstream
- Upstream: `M18`
- Downstream: `M20`
