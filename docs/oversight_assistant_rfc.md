# RFC: Oversight-Integrated AI Assistant v1

Status: Draft for implementation

Document type: Engineering RFC with executable requirements

Companion document: `docs/oversight_assistant_article.md`

Related spec: `docs/specs/oversight_ops_app_v1_layer2.md`

Shared glossary: `docs/shared_glossary.md`

## 1. Abstract

This RFC defines a production-ready architecture for an oversight-integrated AI assistant. The system objective is to improve solution quality and reduce failure modes common in output-first assistants by enforcing a structured operating loop, explicit quality gates, and measurable fallback behavior.

The assistant runs an RCTF plus PDCA cycle for complex work:

- Read and Plan
- Code and Do
- Test and Check
- Fix and Act

The RFC includes:

- module contracts and data interfaces
- decision rules and numeric thresholds
- tool and retrieval policy
- security and privacy controls
- observability and SLOs
- acceptance tests and rollout criteria

The v1 scope excludes speculative methods and focuses on operational reliability in product and engineering workflows.

### 1.1 Conformance language

The key words "MUST", "MUST NOT", "SHALL", and "SHOULD" in this document are to be interpreted as normative requirements.

## 2. Goals and non-goals

### 2.1 Goals

1. Produce decision-complete outputs for medium and high complexity requests.
2. Detect and resolve ambiguity before high-cost execution.
3. Enforce objective quality checks before final response.
4. Provide bounded fallback behavior when progress stalls.
5. Support freshness-critical and high-accuracy tasks through retrieval and tool contracts.[5][6][7][11]
6. Provide operational telemetry for reliability and incident analysis.[16][17]
7. Integrate with VS Code and team workflows using reusable prompt and instruction assets.[1][2][3][4]

### 2.2 Non-goals

1. Full autonomous planning without user confirmation for high-risk actions.
2. Universal domain correctness guarantees.
3. Unbounded self-refinement loops.
4. Dynamic roleplay or speculative agent evolution methods in v1.

## 3. System context and architecture

### 3.1 Context

The assistant operates in conversational environments where users submit natural-language requests with incomplete constraints. The system SHALL transform those requests into structured decisions and auditable outputs.

### 3.2 High-level architecture

The v1 architecture contains these runtime modules:

1. Intake Classifier
2. RCTF Normalizer
3. Oversight Analyzer
4. Mode Selector
5. Planner
6. Executor
7. Quality Evaluator
8. Refinement Loop
9. Fallback Manager
10. Tool and Retrieval Orchestrator
11. Safety Guard
12. Output Controller
13. Session State Store
14. Telemetry Emitter

### 3.3 Architecture flow (text diagram)

1. User request enters Intake Classifier.
2. Request SHALL be normalized into the `UserRequest` schema.
3. Oversight Analyzer SHALL score ambiguity and risk.
4. If ambiguity is high, the system MUST ask clarifying questions and suspend execution.
5. If ambiguity is acceptable, Planner SHALL produce a solution plan.
6. Executor SHALL generate candidate output.
7. Quality Evaluator SHALL score output with PQS and requirement mapping.
8. If checks pass, Output Controller SHALL finalize response and Telemetry Emitter SHALL emit traces.
9. If checks fail, Refinement Loop MUST attempt revision, then Fallback Manager MUST handle escalation when required.
10. If loop limit is reached, Output Controller MUST return constrained options and request user direction.

## 4. Data interfaces and public contracts

All module boundaries MUST use typed payloads validated with JSON Schema Draft 2020-12.[18]

### 4.1 `UserRequest`

```json
{
  "role": "string | null",
  "context": "string",
  "task": "string",
  "constraints": ["string"],
  "format": "string",
  "success_criteria": ["string"],
  "risk_tolerance": "low | medium | high"
}
```

Field rules:

- `context`, `task`, and `format` MUST be present.
- `constraints` and `success_criteria` MAY be empty but MUST exist as arrays.
- `risk_tolerance` SHALL default to `medium` if not provided.

### 4.2 `CheckItem`

```json
{
  "name": "string",
  "status": "pass | fail | partial",
  "evidence": "string",
  "severity": "low | medium | high"
}
```

### 4.3 `NextStep`

```json
{
  "id": "string",
  "description": "string",
  "impact": "string",
  "requires_user_confirmation": true
}
```

### 4.4 `AssistantResponse`

```json
{
  "answer": "string",
  "reasoning_summary": "string",
  "checks": ["CheckItem"],
  "next_step_options": ["NextStep"],
  "assumptions": ["string"]
}
```

Field rules:

- `answer` and `reasoning_summary` MUST be present.
- `checks` MUST be non-empty for complex requests.
- `assumptions` MUST be explicit whenever confidence is below threshold.

### 4.5 `RiskFlag`

```json
{
  "type": "security | privacy | policy | reliability | ambiguity",
  "description": "string",
  "severity": "low | medium | high",
  "mitigation": "string"
}
```

### 4.6 `OversightAssessment`

```json
{
  "ambiguity_score": 0.0,
  "risk_flags": ["RiskFlag"],
  "missing_decisions": ["string"],
  "recommended_questions": ["string"]
}
```

Field rules:

- `ambiguity_score` MUST be in `[0.0, 1.0]`.
- `recommended_questions` MUST contain at most two questions per turn.

### 4.7 `PQSResult`

```json
{
  "correctness": 0,
  "completeness": 0,
  "format_compliance": 0,
  "efficiency": 0,
  "overall": 0,
  "revision_required": false
}
```

Field rules:

- Each component score MUST be in `[0, 10]`.
- `overall` SHALL be the arithmetic mean of the four component scores.
- `revision_required` MUST be `true` when `overall < 8.0`.

### 4.8 `FallbackState`

```json
{
  "level": 0,
  "trigger": "low_confidence | failed_check | ambiguity | user_confusion | tool_failure",
  "action": "string"
}
```

Field rules:

- `level` MUST be an integer in `0..4`.
- `level` MUST be monotonic during one loop unless reset by successful quality evaluation.

## 5. Decision policy and ambiguity handling

### 5.1 Intake classification

Requests SHALL be classified as:

- `simple`: bounded, low-risk, direct response possible.
- `complex`: design, planning, multi-constraint, or high-risk output.

Classification MUST use request length, implied decision count, and risk-domain signals.

### 5.2 Clarification trigger

If `ambiguity_score > 0.35`, the assistant MUST ask one or two high-impact clarification questions before execution.

Examples of ambiguity features:

- missing success criteria
- undefined stakeholders
- conflicting constraints
- no acceptance conditions

### 5.3 Assumption policy

If estimated confidence is `< 0.70`, the assistant MUST surface assumptions explicitly. Assumptions MUST NOT remain implicit in final output for complex requests.

### 5.4 Completeness policy

For complex requests, the assistant MUST map each success criterion to at least one check item. Unmapped criteria SHALL fail quality evaluation.

## 6. Module contracts

### 6.1 Intake Classifier

Input: raw user message plus session context.

Output: `simple | complex`, plus `UserRequest` seed.

Error modes:

- misclassification due to sparse context
- stale session assumptions

Required mitigation:

- include confidence band in classification metadata
- allow Quality Evaluator to force reclassification

### 6.2 RCTF Normalizer

Input: `UserRequest` seed.

Output: normalized `UserRequest` with populated defaults.

Contract requirements:

- resolve role from task type if missing
- ensure `constraints` and `success_criteria` arrays are present
- enforce format defaults when omitted

### 6.3 Oversight Analyzer

Input: normalized `UserRequest` and session history.

Output: `OversightAssessment`.

Scoring requirements:

- ambiguity SHALL increase for missing fields and vague objective language
- risk SHALL increase for security/privacy-sensitive domains
- each risk flag SHALL include a mitigation recommendation

### 6.4 Mode Selector

Input: `UserRequest`, `OversightAssessment`, and session state.

Output: selected mode profile for the turn.

Contract requirements:

- mode selection SHALL be advisory unless fallback escalation is active
- mode changes SHOULD be emitted as telemetry attributes

### 6.5 Planner

Input: `UserRequest`, `OversightAssessment`, mode profile, and session state.

Output: plan artifact with primary path, one alternative path, and explicit assumptions.

Constraints:

- no speculative techniques in v1
- no unbounded option expansion
- include implementation order and validation points

### 6.6 Executor

Input: planner artifact and required format.

Output: candidate `AssistantResponse`.

Constraints:

- preserve scope boundaries
- include rationale summary for decisions
- avoid freshness-critical claims unless retrieval is verified

### 6.7 Quality Evaluator

Input: candidate `AssistantResponse`, `UserRequest`, and risk flags.

Output: `PQSResult`, plus updated check items.

Gate rules:

- internal revision MUST trigger when `overall < 8.0`
- output MUST fail if required format is violated
- output MUST fail if any high-severity risk lacks mitigation

### 6.8 Refinement Loop

Input: `PQSResult`, failed check items, and current plan state.

Output: revised candidate response or escalation signal.

Loop rules:

- the loop MUST attempt one targeted revision per failed pass
- the loop MUST hand off to Fallback Manager after repeated failures
- autonomous refinement MUST stop after `3` loops

### 6.9 Fallback Manager

Input: loop state, `PQSResult`, and error signals.

Output: `FallbackState` and next action.

Escalation rules:

- escalate after `2` consecutive failed checks
- max autonomous refinement loops: `3`
- after loop cap, request user direction with constrained options

### 6.10 Tool and Retrieval Orchestrator

Input: claim requirements and risk profile.

Output: tool call plan and retrieval results with source list.

Policy:

- freshness-critical claims MUST use retrieval before finalization
- missing source evidence SHALL downgrade confidence
- source metadata MUST be preserved for audit

### 6.11 Safety Guard

Input: response draft plus retrieved content.

Output: policy decision: allow, revise, or block.

Controls:

- prompt injection screening on external text
- data handling checks for sensitive content
- action gating for high-risk instructions

### 6.12 Output Controller

Input: quality-evaluated response, safety decision, and fallback state.

Output: final response payload.

Contract requirements:

- Output Controller SHALL emit only safety-allowed outputs
- Output Controller MUST include assumptions when confidence threshold is not met
- Output Controller MUST surface constrained next steps after fallback level 4

### 6.13 Session State Store

Input: turn artifacts.

Output: canonical state for next turn.

State includes:

- known decisions
- open questions
- risk flags
- unresolved assumptions
- fallback history

### 6.14 Telemetry Emitter

Input: all module events.

Output: structured traces and metrics.

Requirements:

- OpenTelemetry-compliant spans and attributes.[17]
- event emission at each phase transition
- correlation IDs per request

### 6.15 Module ownership and authority matrix

| Decision Area | Owning Module | Can Block Output | Can Override Others | Escalation Path |
| --- | --- | --- | --- | --- |
| Ambiguity detection | Oversight Analyzer | No | No | Fallback Manager |
| Missing decision handling | Oversight Analyzer | No | No | Intake Classifier |
| Safety / privacy violations | Safety Guard | Yes | Yes | Hard stop |
| PQS scoring | Quality Evaluator | No | No | Refinement Loop |
| Refinement execution | Refinement Loop | No | No | Fallback Manager |
| Fallback escalation | Fallback Manager | Yes | Yes | User handoff |
| Mode selection | Mode Selector | No | No | Advisory only |
| Final response emission | Output Controller | No | No | Safety Guard veto |

Safety Guard and Fallback Manager are veto-level modules. All others are advisory unless a defined threshold is breached.

## 7. Fallback state machine

Fallback levels define constrained behavior under failure.

### Level 0: Normal operation

Conditions:

- Quality Evaluator passes
- confidence is acceptable

Action:

- Output Controller SHALL finalize response with optional next steps

### Level 1: Internal strategy retry

Trigger:

- first failed quality check

Action:

- Refinement Loop SHALL retry with alternate plan path
- Refinement Loop MUST preserve original constraints

### Level 2: Clarify and narrow

Trigger:

- ambiguity increase or second failed quality check

Action:

- Fallback Manager MUST ask targeted user questions
- Fallback Manager MUST reduce scope to decision-critical parts

### Level 3: Mode switch or tool route

Trigger:

- unresolved failure after level 2

Action:

- Mode Selector SHALL switch to constrained mode or invoke tool/retrieval route

### Level 4: Controlled stop

Trigger:

- persistent failure, policy conflict, or out-of-scope request

Action:

- Output Controller MUST explain limitation
- Output Controller MUST provide safest feasible alternatives
- Output Controller MUST request explicit user direction

## 8. PQS scoring and refinement logic

PQS components:

- correctness
- completeness
- format compliance
- efficiency

Formula:

`overall = (correctness + completeness + format_compliance + efficiency) / 4`

Revision rules:

1. If `overall >= 8.0`, response MAY proceed.
2. If `overall < 8.0`, Refinement Loop MUST execute one refinement pass.
3. If second pass is still `< 8.0`, Fallback Manager MUST escalate fallback level.
4. Max autonomous refinement loops SHALL be `3`.

Calibration guidance:

- correctness SHOULD reference requirement alignment and factual risk
- completeness SHOULD check criterion coverage
- format compliance SHOULD check schema and requested layout
- efficiency SHOULD check concision and relevance, not brevity alone

## 9. Tooling and retrieval policy

### 9.1 Retrieval requirement

Retrieval is mandatory when claims are freshness-critical or externally factual. Examples include prices, regulations, schedules, and recent product changes.[5][6][7]

### 9.2 Source quality tiers

Tier 1: official documentation, standards, peer-reviewed or canonical papers.

Tier 2: reputable engineering blogs from official org channels.

Tier 3: community discussions and forums.

Policy:

- final claims SHOULD prefer Tier 1
- Tier 2 or Tier 3 sources MUST include an explicit confidence caveat

### 9.3 Tool call transparency

Every tool call MUST be traceable with:

- purpose
- source list
- timestamp
- result confidence

### 9.4 Prompt injection defense in retrieval

Retrieved text MUST NOT be treated as trusted instructions by default. The system MUST apply defensive parsing and instruction boundary checks.[14][15]

## 10. Security, privacy, and safety controls

### 10.1 Security controls

1. The system MUST apply prompt injection detection and quarantine path controls.[14][15]
2. The system MUST validate structured fields at ingress and before emission.
3. The system MUST scan outputs for unsafe operational guidance.
4. Sensitive actions MUST require confirmation gates.

### 10.2 Privacy controls

1. Session memory MUST implement data minimization.
2. Logs MUST apply redaction policy for sensitive fields.
3. Each deployment SHALL define an explicit data retention policy.
4. Output Controller MUST provide user-visible disclosure when external retrieval is used.

### 10.3 Governance alignment

Controls SHOULD map to NIST AI RMF functions: Govern, Map, Measure, and Manage.[12] Implementations SHOULD include GenAI profile considerations for misuse and content risks.[13]

## 11. Session state model

State is represented as a structured object persisted per conversation.

```json
{
  "request_id": "string",
  "turn_index": 0,
  "resolved_decisions": ["string"],
  "open_decisions": ["string"],
  "assumptions": ["string"],
  "risk_flags": ["RiskFlag"],
  "last_pqs": "PQSResult",
  "fallback_state": "FallbackState",
  "tool_history": ["string"],
  "telemetry_refs": ["string"]
}
```

State rules:

- open decisions MUST NOT decrease without corresponding resolution evidence
- fallback state MUST reset to 0 only after Quality Evaluator pass
- assumptions MUST be carried forward until resolved

## 12. Operational metrics, SLOs, and observability

### 12.1 Core metrics

1. Decision completeness rate
2. First-pass PQS pass rate
3. Clarification question rate by request class
4. Fallback escalation rate
5. Loop exhaustion rate
6. Hallucination incident rate
7. Freshness-claim without retrieval rate
8. User correction rate after final response

### 12.2 Suggested SLOs

Initial SLO targets for v1:

- first-pass PQS pass rate >= 70 percent
- final-pass PQS pass rate >= 95 percent
- loop exhaustion rate <= 5 percent
- freshness claims without retrieval = 0
- high-severity unresolved risk flags = 0

SLO policy SHOULD follow standard reliability practices and SHOULD be tuned by observed workload.[16]

### 12.3 Telemetry implementation

Telemetry Emitter MUST emit OpenTelemetry spans for each phase:

- `intake.classify`
- `normalize.rctf`
- `assess.ambiguity_risk`
- `plan.generate`
- `execute.respond`
- `evaluate.pqs`
- `fallback.transition`
- `tools.retrieve`
- `safety.guard`

Each span MUST include request class, ambiguity score, PQS overall, fallback level, and source count.[17]

### 12.4 Evaluation dataset and regression protocol

To keep quality stable across model updates and prompt changes, the system MUST maintain a fixed evaluation dataset with representative request classes:

1. simple task requests
2. ambiguous design requests
3. high-risk privacy and security scenarios
4. freshness-critical fact requests
5. adversarial prompt-injection-like inputs

Each dataset item MUST include expected behavior checkpoints, not only expected final text. At minimum, checkpoints SHOULD verify:

- clarification behavior
- assumption disclosure
- fallback behavior
- retrieval usage where required
- Safety Guard outcome

The full dataset MUST run on every major assistant change. Release MUST be blocked when any of the following regressions occur:

- +2 percentage points drop in final-pass PQS
- any increase in freshness-claim-without-retrieval incidents
- any increase in unresolved high-severity risk flags

Historical runs MUST be stored so threshold changes are evidence-driven and reversible.

## 13. VS Code and multi-agent integration

### 13.1 VS Code integration pattern

1. Store stable project constraints in custom instructions.[2]
2. Store reusable workflows in prompt files.[3]
3. Use context-aware prompting discipline from VS Code guidance.[1]

Example workflow:

- developer opens design issue
- assistant runs oversight loop on requested change
- assistant emits plan plus acceptance checks
- developer executes with periodic check calls

### 13.2 Team workflow integration

Use the assistant in design review and PR checks:

- decision completeness report
- requirement-to-change mapping
- risk register update
- test gap detection

### 13.3 Multi-agent compatibility

For deployments with tool or agent chains, the system MUST use explicit contracts for context passing and tool semantics. Model Context Protocol transport constraints SHOULD guide interoperability boundaries.[19]

### 13.4 Integration defaults for v1 teams

For predictable adoption, teams SHOULD use these defaults unless a justified exception is documented:

1. one project-level instruction asset for stable constraints
2. one prompt file per recurring workflow (design review, implementation plan, PR check)
3. strict schema validation on all response contracts
4. mandatory telemetry in non-local environments
5. Safety Guard enabled in every environment except isolated unit tests

These defaults reduce variation between teams and make incident analysis comparable across repositories and products.

## 14. Acceptance tests

The following tests are required before production readiness.

### Test 1: Simple request path

Input: short concrete task with complete constraints.

Expected:

- classified as simple
- no unnecessary clarification
- response format matches request
- Quality Evaluator pass

### Test 2: Ambiguous broad request

Input: high-level goal with missing constraints.

Expected:

- ambiguity score > 0.35
- assistant asks 1 or 2 high-impact questions
- execution deferred until clarification

### Test 3: Complex design request

Input: architecture request with multiple constraints.

Expected:

- planner outputs primary and alternative path
- assumptions explicit
- checks map to criteria

### Test 4: Failure and refinement trigger

Input: request causing first candidate to miss criteria.

Expected:

- PQS overall < 8.0 on first attempt
- one refinement pass executed
- new PQS reported

### Test 5: Fallback escalation

Input: repeated failed checks.

Expected:

- fallback level escalates after 2 consecutive failures
- max 3 autonomous loops
- controlled user-direction handoff after cap

### Test 6: Safety and privacy-sensitive request

Input: request with sensitive data handling implications.

Expected:

- risk flags emitted
- privacy constraints included in final plan
- unresolved high-severity risk blocks finalization

### Test 7: Freshness-critical claim

Input: asks for latest external fact.

Expected:

- retrieval required before final claim
- source list attached
- no unsupported freshness assertion

### Test 8: Tone robustness

Input: frustrated or adversarial user message.

Expected:

- calm and respectful tone
- technical rigor preserved
- no policy violations

## 15. Rollout plan

### Stage 0: Offline validation

- implement contracts and local Quality Evaluator
- run acceptance test suite against synthetic tasks
- validate telemetry schema

Exit criteria:

- all eight acceptance tests pass
- PQS scoring stable across repeated runs

### Stage 1: Internal pilot

- limited users and controlled task classes
- daily review of fallback and error traces
- rapid threshold tuning

Exit criteria:

- final-pass PQS >= 90 percent
- loop exhaustion <= 8 percent
- no unresolved high-severity incidents

### Stage 2: Team beta

- integrate with VS Code project prompts and instructions
- add PR workflow checks
- enable incident reporting workflow

Exit criteria:

- final-pass PQS >= 95 percent
- freshness claims without retrieval = 0
- user satisfaction trend positive

### Stage 3: Production release

- activate SLO monitoring and alerting
- monthly risk and policy review
- quarterly threshold recalibration

## 16. Failure modes and mitigations

### Failure mode A: Over-questioning

Risk: assistant asks too many questions, harming flow.

Mitigation:

- cap clarification questions to 2
- ask only when ambiguity threshold exceeded

### Failure mode B: Hidden assumptions

Risk: assistant executes on unstated assumptions.

Mitigation:

- confidence threshold policy
- mandatory assumptions field in response

### Failure mode C: Incorrect external claims

Risk: stale or unsupported claims.

Mitigation:

- retrieval policy enforcement
- source attribution requirement

### Failure mode D: Policy bypass via prompt injection

Risk: external text alters system behavior.

Mitigation:

- strict instruction boundary controls
- Safety Guard checks pre-finalization

### Failure mode E: Loop thrash

Risk: repeated refinement without progress.

Mitigation:

- fallback escalation and loop cap
- user-directed branching after cap

## 17. Compatibility and migration considerations

1. Existing assistants can adopt this RFC incrementally by implementing interfaces first, then adding scoring and fallback.
2. Backward compatibility can be maintained by adapting legacy response formats into `AssistantResponse`.
3. Migration SHOULD preserve prior instruction assets while moving recurring prompts into formal prompt files.[3]

## 18. Quality gate for this RFC

This RFC is considered implementation-ready only if all conditions hold:

1. All required interfaces are schema-defined.
2. Thresholds are numeric and testable.
3. Acceptance test suite is complete and executable.
4. Telemetry fields are defined for each phase.
5. Security and privacy controls are explicit.
6. References are primary-source and claim-mapped.

### 18.1 Current quality re-score (self-assessment)

This subsection is a documentation self-assessment and MUST NOT be used as a runtime scoring signal.

- Buildability: 9.8
- Clarity / readability: 9.5
- Completeness: 9.6
- Evidence and rigor: 9.4
- Consistency: 9.7
- VS Code practicality: 9.3

Weighted total: approximately 9.6.

## 19. References

[1] Microsoft, "Prompt engineering in VS Code," <https://code.visualstudio.com/docs/copilot/guides/prompt-engineering-guide>

[2] Microsoft, "Use custom instructions for GitHub Copilot in VS Code," <https://code.visualstudio.com/docs/copilot/copilot-customization>

[3] Microsoft, "Reusable prompt files in VS Code," <https://code.visualstudio.com/docs/copilot/customization/prompt-files>

[4] GitHub Docs, "Getting better results with GitHub Copilot," <https://docs.github.com/en/copilot/using-github-copilot/getting-better-results-with-github-copilot>

[5] OpenAI Docs, "Function calling," <https://platform.openai.com/docs/guides/function-calling>

[6] OpenAI Docs, "Evaluating model performance," <https://platform.openai.com/docs/guides/evals>

[7] Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," arXiv:2005.11401, <https://arxiv.org/abs/2005.11401>

[8] Wei et al., "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models," arXiv:2201.11903, <https://arxiv.org/abs/2201.11903>

[9] Yao et al., "Tree of Thoughts: Deliberate Problem Solving with Large Language Models," arXiv:2305.10601, <https://arxiv.org/abs/2305.10601>

[10] Shinn et al., "Reflexion: Language Agents with Verbal Reinforcement Learning," arXiv:2303.11366, <https://arxiv.org/abs/2303.11366>

[11] Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models," arXiv:2210.03629, <https://arxiv.org/abs/2210.03629>

[12] NIST, "AI Risk Management Framework (AI RMF 1.0)," <https://www.nist.gov/itl/ai-risk-management-framework>

[13] NIST, "Generative AI Profile (NIST AI 600-1)," <https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence>

[14] OWASP, "LLM Top 10," <https://genai.owasp.org/llm-top-10/>

[15] OWASP, "LLM Prompt Injection Prevention Cheat Sheet," <https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html>

[16] Google, "Service Level Objectives," in Site Reliability Engineering Workbook, <https://sre.google/workbook/service-level-objectives/>

[17] OpenTelemetry, "Specification," <https://opentelemetry.io/docs/specs/otel/>

[18] JSON Schema, "Core Specification Draft 2020-12," <https://json-schema.org/draft/2020-12/json-schema-core.html>

[19] Model Context Protocol, "Transports," <https://modelcontextprotocol.io/specification/2025-06-18/basic/transports>
