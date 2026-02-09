# Patch Playbook: Oversight Assistant v1 (VS Code Workflow)

## Purpose

This playbook converts validated findings (`F-001` to `F-016`) into an implementation-ready patch sequence. It includes exact text snippets, integration guidance, dependencies, and validation proof.

Source of truth:

- `docs/oversight_assistant_article.md`
- `docs/oversight_assistant_rfc.md`
- `docs/shared_glossary.md`
- `docs/requirements_trace_matrix.md`

Severity rubric:

- `CRITICAL`: unsafe output risk, authority contradiction, dead-end state, or non-implementable contract.
- `HIGH`: likely runtime failure or major quality regression.
- `MEDIUM`: implementable but operational inconsistency/cost likely.
- `LOW`: clarity or ergonomics improvement.

---

## Wave 1: CRITICAL Blocking Fixes (v1-now)

### F-001: `UserRequest.format` intake/contract contradiction

Impacted Requirement IDs:
- `R-4.1-02`

Impacted Requirement IDs:

- `R-4.1-02`

Issue:

- RFC requires non-null `format`, while day-one example and intake reality allow null.

Impact:

- validation/gating ambiguity and inconsistent runtime behavior.

v1/v2 call:

- `v1-now blocker`.

Exact patch snippet:

```diff
--- a/docs/oversight_assistant_rfc.md
+++ b/docs/oversight_assistant_rfc.md
@@ 4.1 `UserRequest`
 {
   "role": "string | null",
   "context": "string",
   "task": "string",
   "constraints": ["string"],
-  "format": "string",
+  "format": "string | null",
   "success_criteria": ["string"],
   "risk_tolerance": "low | medium | high"
 }
 
 Field rules:
- - `context`, `task`, and `format` MUST be present.
+ - `context` and `task` MUST be present.
+ - `format` MAY be null at intake, but MUST be non-null after RCTF Normalizer.
+ - If `format` is null, RCTF Normalizer SHALL set `format` to `assistant_response_v1`.
```

Integration guidance:

- keep intake tolerant; enforce non-null at post-normalization boundary.

Dependencies:

- `F-002`.

Validation proof:

- Test-2 + `normalize.rctf` attr `format_defaulted`.

---

### F-002: normalization boundary not explicitly normative

Impacted Requirement IDs:
- `R-3.3-01`
- `R-4-01`

Impacted Requirement IDs:

- `R-3.3-01`
- `R-4-01`

Issue:

- contract validation timing is implied, not explicit.

Impact:

- enforcement drift between raw ingress and module boundaries.

v1/v2 call:

- `v1-now blocker`.

Exact patch snippet:

```diff
--- a/docs/oversight_assistant_rfc.md
+++ b/docs/oversight_assistant_rfc.md
@@ 3.3 Architecture flow
 2. Request SHALL be normalized into the `UserRequest` schema.
+   Contract validation using JSON Schema SHALL occur at module boundaries AFTER normalization.
+   Raw ingress MAY be partial and SHALL be represented as an IntakeSeed (non-public).
```

Integration guidance:

- separate raw intake object from normalized contract object.

Dependencies:

- none.

Validation proof:

- Test-2 + `normalize.rctf` span preceding contract-gate checks.

---

### F-003: missing deterministic arbitration precedence

Impacted Requirement IDs:
- `R-6.12-02`

Impacted Requirement IDs:

- `R-6.12-02`

Issue:

- veto modules are named, but precedence is not fully operationalized.

Impact:

- inconsistent final emission under mixed outcomes.

v1/v2 call:

- `v1-now blocker`.

Exact patch snippet:

```diff
--- a/docs/oversight_assistant_rfc.md
+++ b/docs/oversight_assistant_rfc.md
@@ 6.12 Output Controller
 Contract requirements:
  - Output Controller SHALL emit only safety-allowed outputs
+ - Output Controller SHALL apply arbitration precedence (highest first):
+   1) Safety Guard
+   2) Fallback Manager
+   3) Quality Evaluator
+   4) Output Controller
+ - If higher-precedence modules conflict, Output Controller MUST emit constrained alternatives or controlled stop output.
```

Integration guidance:

- implement precedence as a single final gate function.
- canonical precedence: `Safety Guard > Fallback Manager > Quality Evaluator > Output Controller`.

Dependencies:

- none.

Validation proof:

- NEW-10 + `safety.guard`, `fallback.transition`, `execute.respond`.

---

### F-004: retrieval-required policy lacks detection mechanism

Impacted Requirement IDs:
- `R-6.10-01`
- `R-7-06`
- `R-10.2-04`

Impacted Requirement IDs:

- `R-6.10-01`
- `R-7-06`
- `R-10.2-04`

Issue:

- retrieval requirement exists, but no claim-level classifier is defined.

Impact:

- zero-incident freshness SLO cannot be reliably enforced.

v1/v2 call:

- `v1-now blocker`.

Exact patch snippet:

```diff
--- a/docs/oversight_assistant_rfc.md
+++ b/docs/oversight_assistant_rfc.md
 @@ 9.1 Retrieval requirement
 Retrieval is mandatory when claims are freshness-critical or externally factual.
+v1 enforcement:
+- Planner or Tool and Retrieval Orchestrator SHALL run a FreshnessClaimClassifier over task and answer outline.
+- If `requires_retrieval=true`, Executor MUST NOT emit final claims until retrieval succeeds.
+- On retrieval failure, Fallback Manager MUST route to constrained alternatives with explicit uncertainty.
```

Integration guidance:

- start with heuristic classifier; fail-safe behavior is "cannot assert latest."

Dependencies:

- none.

Validation proof:

- Test-7 + NEW-9 + `tools.retrieve` and `fallback.transition`.

---

### F-007: `PQSResult` computed fields are not enforced as computed-only

Impacted Requirement IDs:
- none assigned in current matrix.

Impacted Requirement IDs:

- none assigned in current matrix.

Issue:

- `overall` and `revision_required` can be treated as externally supplied values.

Impact:

- gate bypass by injected PQS payloads.

v1/v2 call:

- `v1-now blocker`.

Exact patch snippet:

```diff
--- a/docs/oversight_assistant_rfc.md
+++ b/docs/oversight_assistant_rfc.md
 @@ 4.7 `PQSResult` Field rules
+- `overall` MUST be computed by Quality Evaluator (computed-only).
+- `revision_required` MUST be computed by Quality Evaluator (computed-only).
+- Implementations MUST ignore inbound values for computed-only fields.
```

Integration guidance:

- recompute PQS inside Quality Evaluator every cycle.

Dependencies:

- none.

Validation proof:

- Test-4 + `evaluate.pqs` payload integrity assertion.

---

### F-009: deterministic fallback counters missing

Impacted Requirement IDs:
- `R-3.3-08`
- `R-3.3-09`
- `R-3.3-10`
- `R-3.3-11`
- `R-4.8-02`
- `R-6.4-01`
- `R-6.8-01`
- `R-6.8-02`
- `R-6.8-03`
- `R-6.9-01`
- `R-6.12-04`
- `R-7-02`
- `R-7-03`
- `R-7-04`
- `R-7-05`
- `R-8-03`
- `R-8-04`
- `R-8-09`
- `R-8-10`
- `R-11-01`

Impacted Requirement IDs:

- `R-3.3-08`
- `R-3.3-09`
- `R-3.3-10`
- `R-3.3-11`
- `R-4.8-02`
- `R-6.4-01`
- `R-6.8-01`
- `R-6.8-02`
- `R-6.8-03`
- `R-6.9-01`
- `R-6.12-04`
- `R-7-02`
- `R-7-03`
- `R-7-04`
- `R-7-05`
- `R-8-03`
- `R-8-04`
- `R-8-09`
- `R-8-10`
- `R-11-01`

Issue:

- escalation depends on consecutive failures, but counters are not explicit.

Impact:

- non-deterministic loop behavior and inconsistent escalation.

v1/v2 call:

- `v1-now blocker`.

Exact patch snippet:

```diff
--- a/docs/oversight_assistant_rfc.md
+++ b/docs/oversight_assistant_rfc.md
 @@ 4.8 `FallbackState`
 {
   "level": 0,
   "trigger": "low_confidence | failed_check | ambiguity | user_confusion | tool_failure",
-  "action": "string"
+  "action": "string",
+  "consecutive_failed_checks": 0,
+  "refinement_attempt": 0
 }
 Field rules:
+- `consecutive_failed_checks` MUST increment on failed PQS and reset only on pass.
+- `refinement_attempt` MUST be monotonic within a request and capped at 3.
```

Integration guidance:

- persist counters in Session State Store and mirror in telemetry.

Dependencies:

- none.

Validation proof:

- Test-5 + `fallback.transition` attributes for both counters.

---

## Wave 2: HIGH Stabilization Fixes

### F-005: strengthen `RiskFlag` typing with stable code

Impacted Requirement IDs:
- none assigned in current matrix.

Impacted Requirement IDs:

- none assigned in current matrix.

Issue:

- risk aggregation is under-specified without stable machine code.

Impact:

- weak dashboarding, routing, and policy automation.

v1/v2 call:

- `v1-now`.

Exact patch snippet:

```diff
--- a/docs/oversight_assistant_rfc.md
+++ b/docs/oversight_assistant_rfc.md
 @@ 4.5 `RiskFlag`
 {
   "type": "security | privacy | policy | reliability | ambiguity",
+  "code": "string",
   "description": "string",
   "severity": "low | medium | high",
   "mitigation": "string"
 }
+Rules:
+- `code` MUST be stable and machine-aggregatable.
```

Integration guidance:

- align codes to glossary taxonomy and telemetry labels.

Dependencies:

- none.

Validation proof:

- Test-6 + telemetry cardinality checks.

---

### F-006: add ordering semantics for recommended questions

Impacted Requirement IDs:
- none assigned in current matrix.

Impacted Requirement IDs:

- none assigned in current matrix.

Issue:

- no normative priority ordering for max-two questions.

Impact:

- variable question quality and branch reduction.

v1/v2 call:

- `v1-now`.

Exact patch snippet:

```diff
--- a/docs/oversight_assistant_rfc.md
+++ b/docs/oversight_assistant_rfc.md
 @@ 4.6 `OversightAssessment` Field rules
 - `recommended_questions` MUST contain at most two questions per turn.
+- Ordering is normative: index 0 MUST be highest-impact.
```

Integration guidance:

- score and sort by branch-reduction impact.

Dependencies:

- none.

Validation proof:

- Test-2 + NEW question-priority assertion.

---

### F-008: fix PQS weighting stability policy

Impacted Requirement IDs:
- none assigned in current matrix.

Impacted Requirement IDs:

- none assigned in current matrix.

Issue:

- equal weighting exists but policy mutability is not governed.

Impact:

- silent drift in quality gates across teams.

v1/v2 call:

- `v1-now` for fixed weighting; `v2-later` for configurable weighting.

Exact patch snippet:

```diff
--- a/docs/oversight_assistant_rfc.md
+++ b/docs/oversight_assistant_rfc.md
 @@ 8 PQS scoring
- `overall = (correctness + completeness + format_compliance + efficiency) / 4`
+v1 weighting is fixed and normative:
+`overall = (correctness + completeness + format_compliance + efficiency) / 4`
+v2 MAY introduce configurable weights ONLY via versioned policy plus regression gates.
```

Integration guidance:

- treat weights as versioned config artifact, not local tweak.

Dependencies:

- none.

Validation proof:

- Test-4 + release policy assertion.

---

### F-010: assumptions required under high-severity risk too

Impacted Requirement IDs:
- `R-4.4-03`
- `R-4.4-04`
- `R-5.3-01`
- `R-5.3-02`
- `R-6.12-03`

Impacted Requirement IDs:

- `R-4.4-03`
- `R-4.4-04`
- `R-5.3-01`
- `R-5.3-02`
- `R-6.12-03`

Issue:

- assumptions currently tied mainly to confidence threshold.

Impact:

- hidden risk assumptions can bypass explicit disclosure.

v1/v2 call:

- `v1-now`.

Exact patch snippet:

```diff
--- a/docs/oversight_assistant_rfc.md
+++ b/docs/oversight_assistant_rfc.md
 @@ 4.4 `AssistantResponse` Field rules
- `assumptions` MUST be explicit whenever confidence is below threshold.
+ `assumptions` MUST be explicit whenever confidence is below threshold OR any high-severity RiskFlag is present.
```

Integration guidance:

- compose assumption rule from confidence and risk gates.

Dependencies:

- F-005.

Validation proof:

- Test-6 + `execute.respond` assumptions assertion.

---

## Wave 3: MEDIUM and LOW Hardening

### F-011: define explicit redaction enforcement boundary

Impacted Requirement IDs:
- `R-10.2-01`
- `R-10.2-02`
- `R-10.2-03`

Impacted Requirement IDs:

- `R-10.2-01`
- `R-10.2-02`
- `R-10.2-03`

Issue:

- redaction policy exists without concrete placement.

Impact:

- possible sensitive data leakage in telemetry/state.

v1/v2 call:

- `v1-now` minimum boundary; `v2-later` advanced PII detection.

Exact patch snippet:

```diff
--- a/docs/oversight_assistant_rfc.md
+++ b/docs/oversight_assistant_rfc.md
 @@ 10.2 Privacy controls
 2. Logs MUST apply redaction policy for sensitive fields.
+Enforcement:
+- Telemetry Emitter and Session State Store SHALL apply a Redaction Filter before persistence or emission.
```

Integration guidance:

- apply same filter policy to both emit and persist paths.

Dependencies:

- none.

Validation proof:

- NEW-11 + telemetry/state redaction assertions.

---

### F-012: enforce tool-output instruction boundary

Impacted Requirement IDs:
- `R-6.11-01`

Impacted Requirement IDs:

- `R-6.11-01`

Issue:

- untrusted retrieval data boundary is stated but not operationally explicit enough.

Impact:

- prompt-injection control-plane contamination risk.

v1/v2 call:

- `v1-now`.

Exact patch snippet:

```diff
--- a/docs/oversight_assistant_rfc.md
+++ b/docs/oversight_assistant_rfc.md
 @@ 9.4 Prompt injection defense in retrieval
 Retrieved text MUST NOT be treated as trusted instructions by default.
+v1 boundary rule:
+- Tool and retrieval outputs SHALL be treated as untrusted data only.
+- Safety Guard SHALL quarantine instruction-like payloads from control decisions.
```

Integration guidance:

- perform boundary enforcement before planning/evaluation reuse.

Dependencies:

- none.

Validation proof:

- NEW-12 + `safety.guard` quarantine metrics.

---

### F-013: extend acceptance suite for real failure modes

Impacted Requirement IDs:
- `R-6.10-02`
- `R-14-01`

Impacted Requirement IDs:

- `R-6.10-02`
- `R-14-01`

Issue:

- missing scenarios for tool failure, arbitration correctness, source-tier downgrade.

Impact:

- blind spots in production failure envelope.

v1/v2 call:

- `v1-now`.

Exact patch snippet:

```diff
--- a/docs/oversight_assistant_rfc.md
+++ b/docs/oversight_assistant_rfc.md
 @@ 14 Acceptance tests
+### Test 9: Retrieval tool failure on freshness-required claim
+Input: freshness-critical request where retrieval tool fails.
+Expected: no unsupported claim, constrained alternatives, fallback transition logged.
+
+### Test 10: Veto arbitration correctness
+Input: response passes PQS but violates Safety Guard.
+Expected: Safety Guard blocks, Output Controller emits constrained safe alternative.
+
+### Test 11: Source-tier downgrade handling
+Input: freshness-critical request satisfied only by Tier 3 sources.
+Expected: confidence downgrade, explicit caveat, no hard "latest" assertion.
```

Integration guidance:

- add tests to release-gate suite.

Dependencies:

- F-003, F-004.

Validation proof:

- NEW-9, NEW-10, NEW-11 passing in CI.

---

### F-014: article/RFC module-count framing mismatch

Impacted Requirement IDs:
- `R-APP-014-01`

Impacted Requirement IDs:

- `R-APP-014-01`

Issue:

- onboarding can confuse baseline stack vs runtime module set.

Impact:

- implementation misunderstanding risk for new readers.

v1/v2 call:

- `v1-doc-now` or `v2-later`.

Exact patch snippet:

```diff
--- a/docs/oversight_assistant_article.md
+++ b/docs/oversight_assistant_article.md
 @@ Practical module stack
- The v1 stack ... includes eleven modules.
+ The v1 baseline stack is simplified for readability; the RFC runtime model adds persistence and telemetry modules for enforcement and auditability.
```

Integration guidance:

- keep article approachable; RFC remains executable source.

Dependencies:

- none.

Validation proof:

- editorial coherence check.

---

### F-015: glossary RCTF/PDCA mapping clarity

Impacted Requirement IDs:
- `R-APP-015-01`

Impacted Requirement IDs:

- `R-APP-015-01`

Issue:

- minor onboarding ambiguity in phase mapping language.

Impact:

- low runtime risk, moderate teaching friction.

v1/v2 call:

- `v1-doc-now` or `v2-later`.

Exact patch snippet:

```diff
--- a/docs/shared_glossary.md
+++ b/docs/shared_glossary.md
 @@ RCTF
 Read, Code, Test, Fix. In this design it maps to request understanding, execution, verification, and correction.
+Note: PDCA overlays RCTF by treating Read as Read plus Plan, and Fix as Fix plus Act.
```

Integration guidance:

- no runtime impact; improves consistency.

Dependencies:

- none.

Validation proof:

- glossary/article consistency check.

---

### F-016: normative trace expansion uncovered unimplemented requirement coverage

Impacted Requirement IDs:
- `R-1.1-01`
- `R-3.1-01`
- `R-3.3-04`
- `R-3.3-05`
- `R-3.3-06`
- `R-3.3-07`
- `R-4.1-03`
- `R-4.1-04`
- `R-4.4-02`
- `R-4.6-01`
- `R-4.6-02`
- `R-4.7-02`
- `R-4.7-03`
- `R-4.7-04`
- `R-4.8-01`
- `R-5.1-01`
- `R-5.1-02`
- `R-6.3-02`
- `R-6.3-03`
- `R-6.3-04`
- `R-6.4-02`
- `R-6.7-03`
- `R-6.10-03`
- `R-6.13-01`
- `R-7-01`
- `R-7-08`
- `R-7-09`
- `R-7-10`
- `R-8-07`
- `R-8-08`
- `R-8-11`
- `R-8-12`
- `R-9.2-01`
- `R-9.2-02`
- `R-9.3-01`
- `R-10.1-03`
- `R-10.1-04`
- `R-10.1-05`
- `R-10.1-06`
- `R-10.3-01`
- `R-11-02`
- `R-12.2-01`
- `R-12.3-01`
- `R-12.4-02`
- `R-12.4-03`
- `R-12.4-04`
- `R-13.3-01`
- `R-13.4-01`
- `R-17-01`
- `R-18.1-01`

Impacted Requirement IDs:

- `R-1.1-01`
- `R-3.1-01`
- `R-3.3-04`
- `R-3.3-05`
- `R-3.3-06`
- `R-3.3-07`
- `R-4.1-03`
- `R-4.1-04`
- `R-4.4-02`
- `R-4.6-01`
- `R-4.6-02`
- `R-4.7-02`
- `R-4.7-03`
- `R-4.7-04`
- `R-4.8-01`
- `R-5.1-01`
- `R-5.1-02`
- `R-6.3-02`
- `R-6.3-03`
- `R-6.3-04`
- `R-6.4-02`
- `R-6.7-03`
- `R-6.10-03`
- `R-6.13-01`
- `R-7-01`
- `R-7-08`
- `R-7-09`
- `R-7-10`
- `R-8-07`
- `R-8-08`
- `R-8-11`
- `R-8-12`
- `R-9.2-01`
- `R-9.2-02`
- `R-9.3-01`
- `R-10.1-03`
- `R-10.1-04`
- `R-10.1-05`
- `R-10.1-06`
- `R-10.3-01`
- `R-11-02`
- `R-12.2-01`
- `R-12.3-01`
- `R-12.4-02`
- `R-12.4-03`
- `R-12.4-04`
- `R-13.3-01`
- `R-13.4-01`
- `R-17-01`
- `R-18.1-01`

Issue:

- Core RFC normative requirements remain unimplemented or unverified and are currently defaulted to `gap`.

Impact:

- Release readiness cannot be claimed for these requirements until ownership and proof are added.

v1/v2 call:

- `v1-now`.

Integration guidance:

- Triage impacted requirements by section, assign owner, and replace placeholder telemetry/test evidence.

Dependencies:

- none.

Validation proof:

- Requirement-specific tests and telemetry assertions added for each impacted requirement.

## Cross-Finding Dependencies

- F-001 depends on F-002 for boundary semantics.
- F-003 depends on no other finding, but F-013 Test 10 depends on F-003.
- F-004 depends on no other finding, but F-013 Test 9 depends on F-004.
- F-010 depends on F-005 for stable high-severity risk taxonomy.
- F-011 and F-012 reinforce Safety Guard and telemetry boundaries used by F-003 and F-004.

## Acceptance Test Additions (Explicit)

- Test 9: retrieval tool failure under freshness-required claim.
- Test 10: veto arbitration correctness.
- Test 11: source-tier downgrade handling.
- Optional NEW-12: untrusted tool-output boundary and quarantine behavior.

## Go/No-Go Checklist

Verdict: `Ready-with-conditions`.

Must be true before implementation translation:

- [ ] F-001 patched (`format` intake/post-normalization boundary).
- [ ] F-002 patched (post-normalization contract validation boundary).
- [ ] F-003 patched (deterministic arbitration precedence).
- [ ] F-004 patched (FreshnessClaimClassifier and failure behavior).
- [ ] F-007 patched (computed-only PQS fields).
- [ ] F-009 patched (deterministic fallback counters).
- [ ] Test 9, Test 10, Test 11 added and passing.

No-Go triggers:

- unresolved authority contradiction about who can block output.
- any path where freshness-critical claim can assert without retrieval evidence.
- non-deterministic consecutive-failure handling for fallback escalation.

## Rollout Integrity

- Wave 1 must complete before any runtime implementation scaffold.
- Wave 2 may run in parallel with integration hardening after Wave 1 closes.
- Wave 3 can be staged with doc and policy refinement.
