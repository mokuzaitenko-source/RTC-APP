# Requirements Trace Matrix: Oversight-Integrated AI Assistant (VS Code v1)

## Purpose
This artifact maps RFC normative requirements to implementation ownership, enforcement points, telemetry proof, and test coverage.

## Source Documents
- `docs/oversight_assistant_article.md`
- `docs/oversight_assistant_rfc.md`
- `docs/shared_glossary.md`
- `docs/patch_playbook.md`

## Matrix Legend
- `hard gate`: blocks output or execution.
- `soft gate`: forces clarification or refinement before progressing.
- `verification gate`: proved by test and/or telemetry assertion rather than direct blocking.

## Core Requirement Trace (One Row Per RFC Normative Line)
| Req ID | Normative Requirement | Source | Owner | Enforcement Type | Enforcement Point | VS Code Implementation | Data Fields | Telemetry Proof | Test | Status | Finding |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-1.1-01 | The key words "MUST", "MUST NOT", "SHALL", and "SHOULD" in this document are to be interpreted as normative requirements. | RFC 1.1:L37 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-3.1-01 | The assistant operates in conversational environments where users submit natural-language requests with incomplete constraints. The system SHALL transform those requests into structured decisions and auditable outputs. | RFC 3.1:L62 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-3.3-01 | Request SHALL be normalized into the `UserRequest` schema. | RFC 3.3:L86 | RCTF Normalizer | hard gate | post-normalization boundary | prompt file | `UserRequest.*` | `normalize.rctf` span | Test-2 | partial | F-002 |
| R-3.3-04 | Oversight Analyzer SHALL score ambiguity and risk. | RFC 3.3:L87 | Oversight Analyzer | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-3.3-05 | If ambiguity is high, the system MUST ask clarifying questions and suspend execution. | RFC 3.3:L88 | Executor | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-3.3-06 | If ambiguity is acceptable, Planner SHALL produce a solution plan. | RFC 3.3:L89 | Quality Evaluator | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-3.3-07 | Executor SHALL generate candidate output. | RFC 3.3:L90 | Output Controller | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-3.3-08 | Quality Evaluator SHALL score output with PQS and requirement mapping. | RFC 3.3:L91 | Refinement Loop | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-3.3-09 | If checks pass, Output Controller SHALL finalize response and Telemetry Emitter SHALL emit traces. | RFC 3.3:L92 | Output Controller | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-3.3-10 | If checks fail, Refinement Loop MUST attempt revision, then Fallback Manager MUST handle escalation when required. | RFC 3.3:L93 | Refinement Loop | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-3.3-11 | If loop limit is reached, Output Controller MUST return constrained options and request user direction. | RFC 3.3:L94 | Output Controller | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-4-01 | All module boundaries MUST use typed payloads validated with JSON Schema Draft 2020-12.[18] | RFC 4:L98 | RCTF Normalizer | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-002 |
| R-4.1-01 | `context`, `task`, and `format` MUST be present. | RFC 4.1:L116 | Intake Classifier | hard gate | intake boundary | prompt file | `UserRequest.context`, `UserRequest.task` | `intake.classify` span | Test-1 | covered | - |
| R-4.1-03 | `constraints` and `success_criteria` MAY be empty but MUST exist as arrays. | RFC 4.1:L117 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-4.1-04 | `risk_tolerance` SHALL default to `medium` if not provided. | RFC 4.1:L118 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-4.4-03 | `answer` and `reasoning_summary` MUST be present. | RFC 4.4:L156 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-010 |
| R-4.4-02 | `checks` MUST be non-empty for complex requests. | RFC 4.4:L157 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-4.4-04 | `assumptions` MUST be explicit whenever confidence is below threshold. | RFC 4.4:L158 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-010 |
| R-4.6-01 | `ambiguity_score` MUST be in `[0.0, 1.0]`. | RFC 4.6:L184 | Oversight Analyzer | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-4.6-02 | `recommended_questions` MUST contain at most two questions per turn. | RFC 4.6:L185 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-4.7-03 | Each component score MUST be in `[0, 10]`. | RFC 4.7:L202 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-4.7-02 | `overall` SHALL be the arithmetic mean of the four component scores. | RFC 4.7:L203 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-4.7-04 | `revision_required` MUST be `true` when `overall < 8.0`. | RFC 4.7:L204 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-4.8-01 | `level` MUST be an integer in `0..4`. | RFC 4.8:L218 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-4.8-02 | `level` MUST be monotonic during one loop unless reset by successful quality evaluation. | RFC 4.8:L219 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-5.1-01 | Requests SHALL be classified as: | RFC 5.1:L225 | Intake Classifier | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-5.1-02 | Classification MUST use request length, implied decision count, and risk-domain signals. | RFC 5.1:L230 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-5.2-01 | If `ambiguity_score > 0.35`, the assistant MUST ask one or two high-impact clarification questions before execution. | RFC 5.2:L234 | Oversight Analyzer | soft gate | pre-plan gate | prompt file | `OversightAssessment.ambiguity_score`, `recommended_questions` | `assess.ambiguity_risk` span | Test-2 | covered | - |
| R-5.3-01 | If estimated confidence is `< 0.70`, the assistant MUST surface assumptions explicitly. Assumptions MUST NOT remain implicit in final output for complex requests. | RFC 5.3:L245 | Output Controller | hard gate | pre-emission gate | output gate | `AssistantResponse.assumptions` | `execute.respond` attr `assumptions_count` | Test-6 | partial | F-010 |
| R-5.4-01 | For complex requests, the assistant MUST map each success criterion to at least one check item. Unmapped criteria SHALL fail quality evaluation. | RFC 5.4:L249 | Quality Evaluator | hard gate | evaluation gate | prompt file | `UserRequest.success_criteria`, `AssistantResponse.checks` | `evaluate.pqs` attr `criteria_coverage` | Test-3 | covered | - |
| R-6.3-03 | ambiguity SHALL increase for missing fields and vague objective language | RFC 6.3:L289 | Oversight Analyzer | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-6.3-02 | risk SHALL increase for security/privacy-sensitive domains | RFC 6.3:L290 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-6.3-04 | each risk flag SHALL include a mitigation recommendation | RFC 6.3:L291 | Oversight Analyzer | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-6.4-01 | mode selection SHALL be advisory unless fallback escalation is active | RFC 6.4:L301 | Mode Selector | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-6.4-02 | mode changes SHOULD be emitted as telemetry attributes | RFC 6.4:L302 | Telemetry Emitter | verification gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-6.7-01 | internal revision MUST trigger when `overall < 8.0` | RFC 6.7:L336 | Quality Evaluator | soft gate | PQS gate | prompt file | `PQSResult.*` | `evaluate.pqs` span | Test-4 | covered | - |
| R-6.7-03 | output MUST fail if required format is violated | RFC 6.7:L337 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-6.7-02 | output MUST fail if any high-severity risk lacks mitigation | RFC 6.7:L338 | Quality Evaluator | hard gate | PQS gate | prompt file | `RiskFlag.severity`, `PQSResult` | `evaluate.pqs` + `safety.guard` | Test-6 | covered | - |
| R-6.8-02 | the loop MUST attempt one targeted revision per failed pass | RFC 6.8:L348 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-6.8-03 | the loop MUST hand off to Fallback Manager after repeated failures | RFC 6.8:L349 | Fallback Manager | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-6.8-01 | autonomous refinement MUST stop after `3` loops | RFC 6.8:L350 | Refinement Loop | hard gate | loop controller | prompt file | `FallbackState.refinement_attempt` (proposed) | `fallback.transition` span | Test-5 | partial | F-009 |
| R-6.10-01 | freshness-critical claims MUST use retrieval before finalization | RFC 6.10:L372 | Tool and Retrieval Orchestrator | hard gate | pre-assertion gate | tool hook | claim plan, source list | `tools.retrieve` span | Test-7 | gap | F-004 |
| R-6.10-02 | missing source evidence SHALL downgrade confidence | RFC 6.10:L373 | Tool and Retrieval Orchestrator | soft gate | retrieval result handling | tool hook | confidence metadata | `tools.retrieve` attr `source_tier_max` | NEW-11 | partial | F-013 |
| R-6.10-03 | source metadata MUST be preserved for audit | RFC 6.10:L374 | Tool and Retrieval Orchestrator | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-6.12-01 | Output Controller SHALL emit only safety-allowed outputs | RFC 6.12:L396 | Output Controller | hard gate | final emission gate | output gate | final response payload | `execute.respond` + `safety.guard` | Test-6 | covered | - |
| R-6.12-03 | Output Controller MUST include assumptions when confidence threshold is not met | RFC 6.12:L397 | Output Controller | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-010 |
| R-6.12-04 | Output Controller MUST surface constrained next steps after fallback level 4 | RFC 6.12:L398 | Fallback Manager | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-7-01 | Output Controller SHALL finalize response with optional next steps | RFC 7:L454 | Output Controller | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-7-02 | Refinement Loop SHALL retry with alternate plan path | RFC 7:L464 | Refinement Loop | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-7-03 | Refinement Loop MUST preserve original constraints | RFC 7:L465 | Refinement Loop | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-7-04 | Fallback Manager MUST ask targeted user questions | RFC 7:L475 | Fallback Manager | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-7-05 | Fallback Manager MUST reduce scope to decision-critical parts | RFC 7:L476 | Fallback Manager | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-7-06 | Mode Selector SHALL switch to constrained mode or invoke tool/retrieval route | RFC 7:L486 | Mode Selector | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-004 |
| R-7-09 | Output Controller MUST explain limitation | RFC 7:L496 | Output Controller | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-7-08 | Output Controller MUST provide safest feasible alternatives | RFC 7:L497 | Output Controller | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-7-10 | Output Controller MUST request explicit user direction | RFC 7:L498 | Output Controller | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-8-03 | If `overall >= 8.0`, response MAY proceed. | RFC 8:L515 | Fallback Manager | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-8-04 | If `overall < 8.0`, Refinement Loop MUST execute one refinement pass. | RFC 8:L516 | Refinement Loop | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-8-09 | If second pass is still `< 8.0`, Fallback Manager MUST escalate fallback level. | RFC 8:L517 | Fallback Manager | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-8-10 | Max autonomous refinement loops SHALL be `3`. | RFC 8:L518 | Refinement Loop | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-8-07 | correctness SHOULD reference requirement alignment and factual risk | RFC 8:L522 | Architecture Governance | verification gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-8-08 | completeness SHOULD check criterion coverage | RFC 8:L523 | Architecture Governance | verification gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-8-11 | format compliance SHOULD check schema and requested layout | RFC 8:L524 | Architecture Governance | verification gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-8-12 | efficiency SHOULD check concision and relevance, not brevity alone | RFC 8:L525 | Architecture Governance | verification gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-9.2-01 | final claims SHOULD prefer Tier 1 | RFC 9.2:L543 | Architecture Governance | verification gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-9.2-02 | Tier 2 or Tier 3 sources MUST include an explicit confidence caveat | RFC 9.2:L544 | Tool and Retrieval Orchestrator | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-9.3-01 | Every tool call MUST be traceable with: | RFC 9.3:L548 | Tool and Retrieval Orchestrator | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-6.11-01 | Retrieved text MUST NOT be treated as trusted instructions by default. The system MUST apply defensive parsing and instruction boundary checks.[14][15] | RFC 9.4:L557 | Safety Guard | hard gate | tool ingest boundary | tool hook | tool payload | `safety.guard` attr `injection_screened` | NEW-12 | gap | F-012 |
| R-10.1-03 | The system MUST apply prompt injection detection and quarantine path controls.[14][15] | RFC 10.1:L563 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-10.1-04 | The system MUST validate structured fields at ingress and before emission. | RFC 10.1:L564 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-10.1-05 | The system MUST scan outputs for unsafe operational guidance. | RFC 10.1:L565 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-10.1-06 | Sensitive actions MUST require confirmation gates. | RFC 10.1:L566 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-10.2-02 | Session memory MUST implement data minimization. | RFC 10.2:L570 | Session State Store | hard gate | state write boundary | prompt file + state filter | state payload | `state.persist` attr `fields_dropped` | Test-6 | partial | F-011 |
| R-10.2-01 | Logs MUST apply redaction policy for sensitive fields. | RFC 10.2:L571 | Telemetry Emitter | verification gate | pre-emit redaction | telemetry assertion | redacted fields | `telemetry.emit` attr `redaction_applied` | NEW-11 | gap | F-011 |
| R-10.2-03 | Each deployment SHALL define an explicit data retention policy. | RFC 10.2:L572 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-011 |
| R-10.2-04 | Output Controller MUST provide user-visible disclosure when external retrieval is used. | RFC 10.2:L573 | Tool and Retrieval Orchestrator | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-004 |
| R-10.3-01 | Controls SHOULD map to NIST AI RMF functions: Govern, Map, Measure, and Manage.[12] Implementations SHOULD include GenAI profile considerations for misuse and content risks.[13] | RFC 10.3:L577 | Architecture Governance | verification gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-6.13-01 | open decisions MUST NOT decrease without corresponding resolution evidence | RFC 11:L600 | Session State Store | verification gate | state persistence | telemetry assertion | `resolved_decisions`, `open_decisions` | `state.persist` attr `delta_open_decisions` | Test-3 | partial | F-016 |
| R-11-01 | fallback state MUST reset to 0 only after Quality Evaluator pass | RFC 11:L601 | Quality Evaluator | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-009 |
| R-11-02 | assumptions MUST be carried forward until resolved | RFC 11:L602 | Session State Store | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-12.2-01 | SLO policy SHOULD follow standard reliability practices and SHOULD be tuned by observed workload.[16] | RFC 12.2:L627 | Architecture Governance | verification gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-12.3-01 | Telemetry Emitter MUST emit OpenTelemetry spans for each phase: | RFC 12.3:L631 | Telemetry Emitter | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-6.14-01 | Each span MUST include request class, ambiguity score, PQS overall, fallback level, and source count.[17] | RFC 12.3:L643 | Telemetry Emitter | verification gate | emit boundary | telemetry assertion | span attrs | `intake.classify`, `assess.ambiguity_risk`, `evaluate.pqs`, `fallback.transition`, `tools.retrieve` | Test-8 | covered | - |
| R-12.4-02 | To keep quality stable across model updates and prompt changes, the system MUST maintain a fixed evaluation dataset with representative request classes: | RFC 12.4:L647 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-12.4-03 | Each dataset item MUST include expected behavior checkpoints, not only expected final text. At minimum, checkpoints SHOULD verify: | RFC 12.4:L655 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-12.4-01 | The full dataset MUST run on every major assistant change. Release MUST be blocked when any of the following regressions occur: | RFC 12.4:L663 | Quality Evaluator | verification gate | release gate | CI workflow assertion | eval run metadata | `eval.run` span | Test-8 | covered | - |
| R-12.4-04 | Historical runs MUST be stored so threshold changes are evidence-driven and reversible. | RFC 12.4:L669 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-13.3-01 | For deployments with tool or agent chains, the system MUST use explicit contracts for context passing and tool semantics. Model Context Protocol transport constraints SHOULD guide interoperability boundaries.[19] | RFC 13.3:L697 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-13.4-01 | For predictable adoption, teams SHOULD use these defaults unless a justified exception is documented: | RFC 13.4:L701 | Architecture Governance | verification gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-17-01 | Migration SHOULD preserve prior instruction assets while moving recurring prompts into formal prompt files.[3] | RFC 17:L890 | Architecture Governance | verification gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |
| R-18.1-01 | This subsection is a documentation self-assessment and MUST NOT be used as a runtime scoring signal. | RFC 18.1:L905 | Architecture Governance | hard gate | TBD | TBD | TBD | TBD | TBD | gap | F-016 |

## Appendix A: Proposed/Unmatched Legacy Requirements
| Req ID | Normative Requirement | Source | Owner | Enforcement Type | Enforcement Point | VS Code Implementation | Data Fields | Telemetry Proof | Test | Status | Finding |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-4.1-02 | `format` MAY be null at intake but MUST be non-null after normalization. | RFC 4.1 (proposed) [legacy-unmatched] | RCTF Normalizer | hard gate | contract boundary | prompt file | `UserRequest.format` | `normalize.rctf` attr `format_defaulted` | Test-2 | gap | F-001 |
| R-5.3-02 | Assumptions MUST be explicit when any high-severity risk is present. | RFC 5.3 (proposed) [legacy-unmatched] | Output Controller | hard gate | pre-emission gate | output gate | `AssistantResponse.assumptions`, `RiskFlag.severity` | `safety.guard` + `execute.respond` | Test-6 | gap | F-010 |
| R-6.9-01 | Fallback escalation MUST occur after 2 consecutive failed checks. | RFC 6.9 [legacy-unmatched] | Fallback Manager | hard gate | escalation controller | prompt file | `FallbackState.consecutive_failed_checks` (proposed) | `fallback.transition` span | Test-5 | partial | F-009 |
| R-6.12-02 | Arbitration precedence MUST be deterministic. | RFC 6.12 (proposed) [legacy-unmatched] | Output Controller | hard gate | arbitration gate | output gate | gate outcomes | `fallback.transition` + `safety.guard` | NEW-10 | gap | F-003 |
| R-14-01 | Acceptance suite MUST include freshness/tool failure, arbitration correctness, and source-tier downgrade behavior. | RFC 14 (proposed) [legacy-unmatched] | Quality Evaluator | verification gate | test suite definition | test harness | test catalog | `eval.run` attr `scenario_id` | NEW-9/10/11 | gap | F-013 |

## Appendix B: Non-RFC Finding Sync
| Req ID | Normative Requirement | Source | Owner | Enforcement Type | Enforcement Point | VS Code Implementation | Data Fields | Telemetry Proof | Test | Status | Finding |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-APP-014-01 | Article framing SHOULD clearly distinguish baseline readability stack from RFC runtime module set. | Article practical module stack [non-RFC] | Documentation Governance | verification gate | editorial boundary | docs update | module list | N/A | editorial coherence check | gap | F-014 |
| R-APP-015-01 | Glossary SHALL make RCTF/PDCA phase overlay explicit for onboarding consistency. | Shared glossary core loop terms [non-RFC] | Documentation Governance | verification gate | editorial boundary | docs update | term mapping | N/A | glossary/article consistency check | gap | F-015 |

## Finding Backlink Index
| Finding | Impacted Req IDs | Count |
| --- | --- | --- |
| F-001 | `R-4.1-02` | 1 |
| F-002 | `R-3.3-01`, `R-4-01` | 2 |
| F-003 | `R-6.12-02` | 1 |
| F-004 | `R-6.10-01`, `R-7-06`, `R-10.2-04` | 3 |
| F-005 | - | 0 |
| F-006 | - | 0 |
| F-007 | - | 0 |
| F-008 | - | 0 |
| F-009 | `R-3.3-08`, `R-3.3-09`, `R-3.3-10`, `R-3.3-11`, `R-4.8-02`, `R-6.4-01`, `R-6.8-01`, `R-6.8-02`, `R-6.8-03`, `R-6.9-01`, `R-6.12-04`, `R-7-02`, `R-7-03`, `R-7-04`, `R-7-05`, `R-8-03`, `R-8-04`, `R-8-09`, `R-8-10`, `R-11-01` | 20 |
| F-010 | `R-4.4-03`, `R-4.4-04`, `R-5.3-01`, `R-5.3-02`, `R-6.12-03` | 5 |
| F-011 | `R-10.2-01`, `R-10.2-02`, `R-10.2-03` | 3 |
| F-012 | `R-6.11-01` | 1 |
| F-013 | `R-6.10-02`, `R-14-01` | 2 |
| F-014 | `R-APP-014-01` | 1 |
| F-015 | `R-APP-015-01` | 1 |
| F-016 | `R-1.1-01`, `R-3.1-01`, `R-3.3-04`, `R-3.3-05`, `R-3.3-06`, `R-3.3-07`, `R-4.1-03`, `R-4.1-04`, `R-4.4-02`, `R-4.6-01`, `R-4.6-02`, `R-4.7-02`, `R-4.7-03`, `R-4.7-04`, `R-4.8-01`, `R-5.1-01`, `R-5.1-02`, `R-6.3-02`, `R-6.3-03`, `R-6.3-04`, `R-6.4-02`, `R-6.7-03`, `R-6.10-03`, `R-6.13-01`, `R-7-01`, `R-7-08`, `R-7-09`, `R-7-10`, `R-8-07`, `R-8-08`, `R-8-11`, `R-8-12`, `R-9.2-01`, `R-9.2-02`, `R-9.3-01`, `R-10.1-03`, `R-10.1-04`, `R-10.1-05`, `R-10.1-06`, `R-10.3-01`, `R-11-02`, `R-12.2-01`, `R-12.3-01`, `R-12.4-02`, `R-12.4-03`, `R-12.4-04`, `R-13.3-01`, `R-13.4-01`, `R-17-01`, `R-18.1-01` | 50 |

## Orphan Analysis
- Requirements mapped to generic finding `F-016`: `50`.
- Strict sync invariant status: `pass` (all gap/partial rows have findings, and findings have matrix backlinks).

## Coverage Summary
- Core traced requirements: `91`
- Core covered: `8`
- Core partial: `6`
- Core gap: `77`
- Appendix A rows: `5`
- Appendix B rows: `2`

## Readiness Gate
Implementation readiness remains `ready-with-conditions` until Wave-1 blockers are patched and verified.
