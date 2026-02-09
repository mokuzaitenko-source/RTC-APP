# Shared Glossary: Oversight-Integrated AI Assistant

This glossary is shared by:

- `docs/oversight_assistant_article.md`
- `docs/oversight_assistant_rfc.md`

## Core loop terms

### RCTF

Read, Code, Test, Fix. In this design it maps to request understanding, execution, verification, and correction.

### PDCA

Plan, Do, Check, Act. Used as the iterative control frame for each substantial task turn.

## Oversight terms

### Ambiguity score

A value from 0.0 to 1.0 that estimates how underspecified a request is. The v1 clarification threshold is `> 0.35`.

### Missing decision

A high-impact unresolved choice that blocks safe execution, such as undefined success criteria or absent constraints.

### High-impact question

A clarification question whose answer changes architecture, scope, risk, or implementation order.

### Assumption

A stated provisional decision used when information is missing. Assumptions must be explicit when confidence is below threshold.

## Module terms

### Oversight Analyzer

Module that computes ambiguity/risk signals, identifies missing decisions, and recommends high-impact clarifying questions.

### Quality Evaluator

Module that evaluates response quality using PQS and determines whether revision is required.

### Refinement Loop

Module that applies targeted revision attempts after failed quality checks and then hands off to fallback escalation.

### Mode Selector

Advisory module that selects interaction mode for the current turn (clarify, plan, evaluate, or execute).

### Safety Guard

Veto-capable module that enforces safety/privacy/policy constraints and can block unsafe output.

### Output Controller

Module that emits the final user-visible response only after quality and safety gating has passed.

## Quality terms

### PQS

Prompt Quality Scorecard. Composite quality check with four components:

- correctness
- completeness
- format compliance
- efficiency

Each component is scored 0 to 10. `overall` is the arithmetic mean.

### Revision required

Boolean set to true when `PQS overall < 8.0`.

## Fallback terms

### Fallback level

Escalation state from 0 to 4 used when checks fail or progress stalls.

- Level 0: normal operation
- Level 1: internal strategy retry
- Level 2: clarify and narrow with user
- Level 3: mode switch or tool route
- Level 4: controlled stop and alternatives

### Loop cap

Maximum autonomous refinement loops per request. The v1 cap is `3`.

### Veto-level module

A module with authority to block or halt output. In v1, Safety Guard and Fallback Manager are veto-level modules.

### Escalation semantics

If a veto-level module blocks output, control MUST escalate to constrained alternatives or explicit user handoff rather than silent continuation.

## Confidence and risk terms

### Confidence threshold

If confidence is `< 0.70`, the response must include explicit assumptions.

### Risk flag

Structured record of identified risk with severity and mitigation. Types include security, privacy, policy, reliability, and ambiguity.

## Retrieval and tooling terms

### Freshness-critical claim

A claim that depends on recent or changing external information. Retrieval is required before final assertion.

### Source tier

Priority class for evidence quality.

- Tier 1: official docs, standards, canonical papers
- Tier 2: official engineering blog guidance
- Tier 3: community discussion

### Tool transparency

Requirement that each tool call logs purpose, source list, timestamp, and confidence.

## Operations terms

### Decision completeness rate

Fraction of complex requests where all required decisions are explicit before finalization.

### First-pass PQS pass rate

Fraction of requests that pass PQS without refinement.

### Loop exhaustion rate

Fraction of requests that hit the loop cap before successful completion.

### Hallucination incident rate

Rate of externally factual claims later found unsupported by verified sources.

## Integration terms

### Custom instructions

Project-level guidance used by Copilot and chat systems to maintain style and constraints across interactions.

### Prompt files

Reusable prompt templates for recurring tasks, stored and versioned with project assets.

### Structured response contract

Response schema requiring `answer`, `reasoning_summary`, `checks`, `next_step_options`, and `assumptions`.
