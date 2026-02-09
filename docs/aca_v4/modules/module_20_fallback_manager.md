# Module 20: Fallback Manager

## Purpose
Apply deterministic fallback routes when integrity/coherence/safety thresholds fail.

## Inputs
- Integrity/coherence flags from `M18` and `M19`.
- Safety override context from `M0`.
- Weighted quality score from `M15`.

## Outputs
- Structured fallback object:
  - `triggered`
  - `reason_code`
  - `strategy`
  - `notes`
- Optional clarify-mode response replacement.
- Trace event with `status=pass|fallback`.

## Process / Pseudocode
```text
reason = none
if prompt_injection_detected: reason = prompt_injection_detected
elif integrity_fail: reason = integrity_check_failed
elif coherence_fail: reason = coherence_check_failed
elif quality_score < threshold: reason = low_quality

if reason != none:
  mark fallback triggered
  for non-safety reasons: replace response with clarify prompt + questions
write fallback object to state/result
emit trace
```

## Safety Checks
- Safety fallback takes precedence over all other fallback reasons.
- Fallback output remains bounded to safe clarify responses when triggered.

## Failure Modes
- Triggered fallback due to safety, integrity, coherence, or low quality.
- No-op pass-through when all guards pass.

## Upstream / Downstream
- Upstream: `M19`
- Downstream: `M21`
