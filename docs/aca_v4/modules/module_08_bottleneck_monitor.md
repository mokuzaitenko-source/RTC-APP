# Module 08: Bottleneck Monitor

## Purpose
Detect complexity/resource pressure and apply constraints.

## Inputs
- ACA state from upstream module.
- Tier authority context (`tier2_bottleneck`).
- Active request payload (`user_input`, `context`, `risk_tolerance`, `model`).

## Outputs
- Updated ACA state for downstream processing.
- Trace event containing module ID, status, and detail.

## Process / Pseudocode
```text
1. Validate inputs and dependencies.
2. Apply module-specific transformation.
3. Emit deterministic trace event.
4. Return updated state for downstream module.
```

## Safety Checks
- Enforce Tier 0 safety precedence over operational logic.
- Reject or redact forbidden memory/prompt-injection patterns when applicable.

## Failure Modes
- Invalid input shape: return controlled fallback state.
- Policy violation: escalate to safety tier handling.

## Upstream / Downstream
- Upstream: `M7`
- Downstream: `M9`
