from __future__ import annotations

from typing import Any, Callable, Dict, List

from app.backend.aca import policies
from app.backend.aca.trace import make_event
from app.backend.aca.types import ACAState

BuildResultFn = Callable[..., Dict[str, object]]


def _append_trace(state: ACAState, *, module_id: str, module_name: str, tier: str, status: str, detail: str) -> None:
    state.trace.append(
        make_event(
            module_id=module_id,
            module_name=module_name,
            tier=tier,  # type: ignore[arg-type]
            status=status,  # type: ignore[arg-type]
            detail=detail,
        )
    )


def _set_output(state: ACAState, module_id: str, payload: Dict[str, Any]) -> None:
    state.module_outputs[module_id] = payload


def _tokens(text: str) -> List[str]:
    return [t for t in "".join(ch if ch.isalnum() else " " for ch in text.lower()).split() if t]


def _normalize_weights(weights: Dict[str, float], safety_floor: float = 0.15) -> Dict[str, float]:
    clean = {k: max(0.0, float(v)) for k, v in weights.items()}
    total = sum(clean.values()) or 1.0
    clean = {k: v / total for k, v in clean.items()}
    if clean.get("safety", 0.0) >= safety_floor:
        return clean
    deficit = safety_floor - clean.get("safety", 0.0)
    keys = [k for k in clean if k != "safety" and clean[k] > 0]
    spread = sum(clean[k] for k in keys) or 1.0
    clean["safety"] = safety_floor
    for key in keys:
        clean[key] = max(0.0, clean[key] - deficit * (clean[key] / spread))
    total2 = sum(clean.values()) or 1.0
    return {k: v / total2 for k, v in clean.items()}


def _task_type(user_input: str) -> str:
    tokens = set(_tokens(user_input))
    if tokens & {"design", "architecture", "system"}:
        return "SYSTEM_DESIGN"
    if tokens & {"plan", "roadmap", "milestone"}:
        return "PLANNING"
    if tokens & {"debug", "fix", "error"}:
        return "TROUBLESHOOTING"
    if tokens & {"explain", "teach"}:
        return "DEEP_EXPLANATION"
    return "FACTUAL_ANSWER"


def _default_quality(result: Dict[str, object]) -> Dict[str, Any]:
    quality = result.get("quality")
    if isinstance(quality, dict):
        return quality
    quality = {
        "clarity": 8,
        "completeness": 8,
        "safety": 9,
        "format_compliance": 8,
        "overall": 8.25,
        "revision_required": False,
    }
    result["quality"] = quality
    return quality


def run_m0_safety_memory_guard(state: ACAState) -> None:
    state.working_input = " ".join(state.request.user_input.split()).strip()
    context = state.request.context.strip() if state.request.context else ""
    state.working_context = context or None
    combo = f"{state.working_input}\n{context}".strip()
    state.prompt_injection_detected = policies.detect_prompt_injection(combo)
    if state.prompt_injection_detected:
        state.meta_policy["safety_override"] = True
    state.safety = {
        "input_safe": not state.prompt_injection_detected,
        "prompt_injection_detected": state.prompt_injection_detected,
        "output_safe": True,
        "blocked": False,
        "threat_level": "high" if state.prompt_injection_detected else "low",
    }
    _set_output(state, "M0", {"prompt_injection_detected": state.prompt_injection_detected, "memory_policy": "session_sanitized_only"})
    _append_trace(
        state,
        module_id="M0",
        module_name="SafetyMemoryGuard",
        tier="tier0_safety",
        status="adjusted" if state.prompt_injection_detected else "pass",
        detail="Prompt-injection detected; safety override engaged." if state.prompt_injection_detected else "Input and memory checks passed.",
    )


def run_m1_identity_gate(state: ACAState) -> None:
    text = f"{state.working_input}\n{state.working_context or ''}".lower()
    state.identity_tag = "ALVIN" if "alvin" in text else ("JAZ" if "jaz" in text else "GENERIC")
    _set_output(state, "M1", {"identity_tag": state.identity_tag})
    _append_trace(state, module_id="M1", module_name="IdentityGate", tier="tier3_operational", status="pass", detail=f"Identity tag selected: {state.identity_tag}.")


def run_m2_preference_loader(state: ACAState) -> None:
    context = (state.working_context or "").lower()
    pacing = "concise" if "concise" in context else ("verbose" if "verbose" in context else "balanced")
    state.preferences = {
        "tone_preference": "technical",
        "pacing_preference": pacing,
        "structural_preference": "mixed",
        "verbosity_level": 2 if pacing == "concise" else (4 if pacing == "verbose" else 3),
    }
    _set_output(state, "M2", state.preferences.copy())
    _append_trace(state, module_id="M2", module_name="PreferenceLoader", tier="tier3_operational", status="pass", detail=f"Preferences loaded: pacing={pacing}.")


def run_m3_meta_controller(state: ACAState) -> None:
    state.meta_policy.update(
        {
            "risk_tolerance": state.request.risk_tolerance,
            "authority": "tier1_meta",
            "safety_locked": bool(state.meta_policy.get("safety_override")),
            "refinement_budgets": {"FAST": 0, "BALANCED": 2, "DEEP": 8},
        }
    )
    _set_output(state, "M3", {"risk_tolerance": state.request.risk_tolerance, "safety_locked": bool(state.meta_policy.get("safety_locked"))})
    _append_trace(state, module_id="M3", module_name="MetaController", tier="tier1_meta", status="adjusted" if state.meta_policy.get("safety_locked") else "pass", detail="Meta policy set.")


def run_m4_mode_system(state: ACAState) -> None:
    mode = "support" if state.meta_policy.get("safety_locked") else "architect"
    state.mode_context = {"mode": mode}
    _set_output(state, "M4", state.mode_context.copy())
    _append_trace(state, module_id="M4", module_name="ModeSystem", tier="tier3_operational", status="pass", detail=f"Mode selected: {mode}.")


def run_m5_path_selector(state: ACAState) -> None:
    length = len(state.working_input)
    path_type = "DEEP" if state.request.risk_tolerance == "high" or length > 180 else ("FAST" if length < 40 else "BALANCED")
    state.path_context = {"path_type": path_type}
    _set_output(state, "M5", {"path_type": path_type, "input_length": length})
    _append_trace(state, module_id="M5", module_name="PathSelector", tier="tier3_operational", status="pass", detail=f"Path selected: {path_type}.")


def run_m6_lands_mixer(state: ACAState) -> None:
    weights = {"clarity": 0.27, "depth": 0.24, "alignment": 0.2, "safety": 0.2, "energy_fit": 0.09}
    if state.path_context.get("path_type") == "DEEP":
        weights["depth"] += 0.11
        weights["clarity"] -= 0.04
    if state.path_context.get("path_type") == "FAST":
        weights["clarity"] += 0.08
        weights["depth"] -= 0.07
    if state.meta_policy.get("safety_locked"):
        weights["safety"] += 0.1
    state.mixer_context = _normalize_weights(weights, safety_floor=0.15)
    _set_output(state, "M6", {"weights": state.mixer_context.copy(), "safety_floor": 0.15})
    _append_trace(state, module_id="M6", module_name="LandsMixer", tier="tier3_operational", status="pass", detail="Mixer weights normalized with safety floor enforcement.")


def run_m7_emotional_regulation(state: ACAState) -> None:
    emotional_load = "high" if "stuck" in state.working_input.lower() else "low"
    tone = "calming" if emotional_load == "high" else "steady"
    state.regulation_context = {"emotional_load": emotional_load, "tone": tone}
    _set_output(state, "M7", state.regulation_context.copy())
    _append_trace(state, module_id="M7", module_name="EmotionalRegulation", tier="tier3_operational", status="pass", detail=f"Regulation profile: {tone}.")


def run_m8_bottleneck_monitor(state: ACAState) -> None:
    path_type = state.path_context.get("path_type", "BALANCED")
    complexity = "high" if path_type == "DEEP" else ("low" if path_type == "FAST" else "medium")
    signal = "force" if complexity == "high" and len(state.working_input) > 420 else "advisory"
    state.bottleneck_context = {"complexity_level": complexity, "signal": signal, "tier": "tier2_bottleneck"}
    _set_output(state, "M8", state.bottleneck_context.copy())
    _append_trace(state, module_id="M8", module_name="BottleneckMonitor", tier="tier2_bottleneck", status="adjusted" if signal == "force" or complexity == "high" else "pass", detail=f"Complexity={complexity}; signal={signal}.")


def run_m9_sparse_attention_dsa(state: ACAState) -> None:
    context = state.working_context or ""
    trimmed = False
    if len(context) > 1800:
        state.working_context = context[:1800].rstrip() + "...[trimmed]"
        trimmed = True
    state.attention_context = {"trimmed": trimmed, "context_chars": len(state.working_context or "")}
    _set_output(state, "M9", state.attention_context.copy())
    _append_trace(state, module_id="M9", module_name="SparseAttentionDSA", tier="tier3_operational", status="adjusted" if trimmed else "pass", detail="Context trimmed by sparse attention policy." if trimmed else "Sparse attention pass-through.")

def run_m10_process_engine(state: ACAState) -> None:
    constraints: List[str] = []
    for line in (state.working_input + "\n" + (state.working_context or "")).split("\n"):
        cleaned = " ".join(line.split()).strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if any(marker in lowered for marker in ["must", "should", "within", "deadline", "cannot", "budget", "risk"]):
            constraints.append(cleaned)
    if not constraints:
        constraints.append("No explicit constraints provided; confirm constraints before irreversible changes.")

    state.process_plan = [
        "Classify objective and detect ambiguity.",
        "Extract constraints and acceptance checks.",
        "Build deterministic execution branches.",
        "Generate response draft aligned to constraints.",
        "Run refinement, integrity, and coherence gates.",
    ]
    payload = {
        "task_type": _task_type(state.working_input),
        "objective": state.working_input,
        "constraints": constraints[:5],
        "acceptance_checks": [
            "Output includes executable steps.",
            "At least one validation/checkpoint step exists.",
            "Fallback behavior is explicit.",
        ],
        "steps": state.process_plan,
    }
    _set_output(state, "M10", payload)
    _append_trace(state, module_id="M10", module_name="ProcessEngine", tier="tier3_operational", status="pass", detail=f"Process engine decomposed task with {len(payload['constraints'])} constraints.")


def run_m11_decision_tree_builder(state: ACAState) -> None:
    branches: List[Dict[str, Any]] = []
    previous: str | None = None
    for idx, step in enumerate(state.process_plan, start=1):
        branch_id = f"B{idx:02d}"
        branches.append({"branch_id": branch_id, "label": step, "type": "execution", "from": previous, "pruned": False})
        previous = branch_id
    if state.meta_policy.get("safety_locked"):
        branches.append({"branch_id": "B_SAFE", "label": "Safety fallback clarification path", "type": "fallback", "from": "B01", "pruned": False})
    state.decision_tree = branches
    state.decision_graph = list(branches)
    _set_output(state, "M11", {"branches": branches, "branch_count": len(branches), "pruning_rule": "prune only contradictory branches"})
    _append_trace(state, module_id="M11", module_name="DecisionTreeBuilder", tier="tier3_operational", status="pass", detail=f"Decision graph built with {len(branches)} branches.")


def run_m12_aim_phase_1(state: ACAState) -> None:
    outline: List[Dict[str, Any]] = []
    for idx, branch in enumerate(state.decision_tree, start=1):
        outline.append(
            {
                "section_id": f"S{idx:02d}",
                "title": branch.get("label", "Untitled"),
                "source_branch_id": branch.get("branch_id", "B00"),
                "kind": "fallback" if branch.get("type") == "fallback" else "core",
            }
        )
    state.outline = outline
    _set_output(state, "M12", {"outline": outline, "section_count": len(outline)})
    _append_trace(state, module_id="M12", module_name="AIMPhase1", tier="tier3_operational", status="pass", detail=f"AIM Phase 1 mapped {len(outline)} sections.")


def run_m13_eve_supra_clean(state: ACAState) -> None:
    contradictions: List[str] = []
    if state.path_context.get("path_type") == "FAST" and state.request.risk_tolerance == "high":
        contradictions.append("FAST path conflicts with high risk tolerance.")
    if state.meta_policy.get("safety_locked") and state.mode_context.get("mode") != "support":
        contradictions.append("Safety lock requires support mode.")
    if state.working_context:
        state.working_context = " ".join(state.working_context.split())
    _set_output(state, "M13", {"contradictions": contradictions, "context_sanitized": bool(state.working_context)})
    _append_trace(
        state,
        module_id="M13",
        module_name="EveSupraClean",
        tier="tier3_operational",
        status="adjusted" if contradictions else "pass",
        detail=f"Supra clean flagged {len(contradictions)} contradictions." if contradictions else "Supra clean checks completed.",
    )


def _injection_safe_result(state: ACAState) -> Dict[str, object]:
    fallback = {
        "triggered": True,
        "reason_code": "prompt_injection_detected",
        "strategy": "safety_clarify",
        "notes": ["Provider execution skipped due to safety policy."],
    }
    return {
        "mode": "clarify",
        "ambiguity_score": 1.0,
        "recommended_questions": [
            "Restate your goal without requesting hidden prompts or policy bypass steps.",
            "List the safe output you want from the assistant.",
        ][: state.request.max_questions],
        "plan": [],
        "candidate_response": "I cannot execute prompt-injection or policy-bypass instructions. Please restate your request safely.",
        "quality": {
            "clarity": 9,
            "completeness": 8,
            "safety": 10,
            "format_compliance": 9,
            "overall": 9.0,
            "revision_required": False,
        },
        "iteration_count": 1,
        "notes": ["prompt_injection_detected", "safety_override_applied"],
        "fallback": fallback,
    }


def run_m14_eve_core(state: ACAState, build_result: BuildResultFn) -> None:
    if state.prompt_injection_detected:
        state.result = _injection_safe_result(state)
        state.fallback = dict(state.result.get("fallback") or {})
        _set_output(state, "M14", {"provider_executed": False, "provider_mode": state.request.provider_mode, "model": state.request.model, "reason": "prompt_injection_detected"})
        _append_trace(state, module_id="M14", module_name="EveCore", tier="tier3_operational", status="fallback", detail="Provider execution skipped due to prompt-injection safety override.")
        return

    result = build_result(
        user_input=state.working_input,
        context=state.working_context,
        risk_tolerance=state.request.risk_tolerance,
        max_questions=state.request.max_questions,
        mode=state.request.provider_mode,
        model=state.request.model,
    )
    state.result = result if isinstance(result, dict) else {}
    _set_output(state, "M14", {"provider_executed": True, "provider_mode": state.request.provider_mode, "model": state.request.model, "result_mode": str(state.result.get("mode") or "unknown")})
    _append_trace(state, module_id="M14", module_name="EveCore", tier="tier3_operational", status="pass", detail="Provider reasoning output received.")


def run_m15_seed_scoring(state: ACAState) -> None:
    quality = _default_quality(state.result)
    weights = _normalize_weights(
        {
            "clarity": float(state.mixer_context.get("clarity", 0.28)),
            "depth": float(state.mixer_context.get("depth", 0.22)),
            "alignment": float(state.mixer_context.get("alignment", 0.2)),
            "safety": float(state.mixer_context.get("safety", 0.2)),
            "energy_fit": float(state.mixer_context.get("energy_fit", 0.1)),
        },
        safety_floor=0.15,
    )
    raw_scores = {
        "clarity": float(quality.get("clarity", 0.0)),
        "depth": float(quality.get("completeness", 0.0)),
        "alignment": float(quality.get("format_compliance", 0.0)),
        "safety": float(quality.get("safety", 0.0)),
        "energy_fit": float(quality.get("overall", 0.0)),
    }
    state.quality_score = round(sum(raw_scores[k] * weights.get(k, 0.0) for k in raw_scores), 2)
    quality["aca_seed_score"] = state.quality_score
    quality["aca_weights"] = {k: round(v, 4) for k, v in weights.items()}
    _set_output(state, "M15", {"weights": weights, "raw_scores": raw_scores, "weighted_score": state.quality_score, "safety_floor": 0.15})
    _append_trace(state, module_id="M15", module_name="SeedScoring", tier="tier3_operational", status="pass", detail=f"Seed quality scored at {state.quality_score:.2f}.")


def run_m16_refinement_loop(state: ACAState) -> None:
    plan = state.result.get("plan") if isinstance(state.result.get("plan"), list) else []
    plan = [" ".join(str(item).split()).strip() for item in plan if str(item).strip()]
    path_type = str(state.path_context.get("path_type", "BALANCED")).upper()
    budget = {"FAST": 0, "BALANCED": 2, "DEEP": 8}.get(path_type, 2)
    modifications: List[str] = []
    if state.result.get("mode") == "plan_execute":
        if not any("gate" in step.lower() for step in plan):
            plan.insert(0, "Input gate: confirm objective, scope, and constraints before execution.")
            modifications.append("added_gate_step")
        if not any(any(token in step.lower() for token in ["acceptance", "verify", "validation", "check"]) for step in plan):
            plan.append("Acceptance check: verify behavior with deterministic tests before handoff.")
            modifications.append("added_acceptance_step")
        if not any("fallback" in step.lower() for step in plan):
            plan.append("Fallback policy: retry with simplified strategy, then request clarification.")
            modifications.append("added_fallback_step")
        while len(plan) < 4:
            plan.append("Execution step: implement the next smallest testable increment.")
            modifications.append("expanded_minimum_depth")
    state.result["plan"] = plan
    current = state.result.get("iteration_count") if isinstance(state.result.get("iteration_count"), int) else 1
    used = 0 if budget == 0 else min(budget, max(1, len(modifications)))
    state.result["iteration_count"] = max(int(current), used)
    _set_output(state, "M16", {"path_type": path_type, "budget": budget, "iterations_used": used, "modifications": modifications})
    _append_trace(state, module_id="M16", module_name="RefinementLoop", tier="tier3_operational", status="adjusted" if modifications else "pass", detail=f"Refinement modifications={len(modifications)} budget={budget}.")


def run_m17_conflict_resolution(state: ACAState) -> None:
    plan = state.result.get("plan") if isinstance(state.result.get("plan"), list) else []
    cleaned: List[str] = []
    seen: set[str] = set()
    for item in plan:
        text = " ".join(str(item).split()).strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            cleaned.append(text)
    strategy = "dedupe" if len(cleaned) != len(plan) else "none"
    if any("cannot" in step.lower() for step in cleaned) and any("must" in step.lower() for step in cleaned):
        strategy = "precedence_safety"
        cleaned = [step for step in cleaned if "must" not in step.lower() or "safe" in step.lower()]
    state.result["plan"] = cleaned
    _set_output(
        state,
        "M17",
        {
            "strategy_cascade": ["safety_precedence", "policy_alignment", "constraint_consistency", "dedupe_merge", "fallback_to_safe_default"],
            "strategy_used": strategy,
            "plan_length": len(cleaned),
        },
    )
    _append_trace(state, module_id="M17", module_name="ConflictResolution", tier="tier3_operational", status="adjusted" if strategy != "none" else "pass", detail=f"Conflict strategy={strategy}.")

def run_m18_task_integrity(state: ACAState) -> None:
    failures: List[str] = []
    mode = str(state.result.get("mode") or "")
    candidate = str(state.result.get("candidate_response") or "").strip()
    plan = state.result.get("plan") if isinstance(state.result.get("plan"), list) else []

    if mode not in {"clarify", "plan_execute"}:
        failures.append("invalid_mode")
    if not candidate:
        failures.append("missing_candidate_response")
    if mode == "plan_execute":
        if len(plan) < 4:
            failures.append("insufficient_plan_depth")
        if not any(any(token in str(step).lower() for token in ["acceptance", "verify", "validation", "check"]) for step in plan):
            failures.append("missing_acceptance_check")
        if not any("fallback" in str(step).lower() for step in plan):
            failures.append("missing_fallback_step")

    passed = not failures
    if not passed:
        state.meta_policy["integrity_fail"] = True
        state.meta_policy.setdefault("fallback_reason", "integrity_check_failed")
        notes = state.result.get("notes") if isinstance(state.result.get("notes"), list) else []
        for failure in failures:
            marker = f"integrity:{failure}"
            if marker not in notes:
                notes.append(marker)
        state.result["notes"] = notes

    _set_output(
        state,
        "M18",
        {
            "pass": passed,
            "failures": failures,
            "checks": {
                "mode_valid": mode in {"clarify", "plan_execute"},
                "candidate_present": bool(candidate),
                "plan_depth_ok": len(plan) >= 4 if mode == "plan_execute" else True,
            },
        },
    )
    _append_trace(state, module_id="M18", module_name="TaskIntegrity", tier="tier3_operational", status="blocked" if failures else "pass", detail=f"Task integrity {'failed' if failures else 'passed'}.")


def run_m19_error_coherence(state: ACAState) -> None:
    issues: List[str] = []
    candidate = str(state.result.get("candidate_response") or "").lower()
    plan = state.result.get("plan") if isinstance(state.result.get("plan"), list) else []

    if candidate and "do not" in candidate and "must" in candidate:
        issues.append("contradictory_instruction_language")
    if state.quality_score and state.quality_score < 6.5:
        issues.append("low_weighted_quality")
    if state.meta_policy.get("integrity_fail"):
        issues.append("upstream_integrity_failure")
    if state.result.get("mode") == "plan_execute" and not plan:
        issues.append("missing_plan_after_refinement")

    passed = not issues
    if not passed:
        state.meta_policy["coherence_fail"] = True
        state.meta_policy.setdefault("fallback_reason", "coherence_check_failed")

    _set_output(state, "M19", {"pass": passed, "issues": issues, "quality_score": state.quality_score})
    _append_trace(state, module_id="M19", module_name="ErrorCoherenceChecker", tier="tier3_operational", status="blocked" if issues else "pass", detail=f"Coherence {'failed' if issues else 'passed'}.")


def run_m20_fallback_manager(state: ACAState) -> None:
    reason_code = "none"
    strategy = "none"
    triggered = False

    if state.prompt_injection_detected:
        reason_code = "prompt_injection_detected"
        strategy = "safety_clarify"
        triggered = True
    elif state.meta_policy.get("integrity_fail"):
        reason_code = "integrity_check_failed"
        strategy = "clarify_missing_requirements"
        triggered = True
    elif state.meta_policy.get("coherence_fail"):
        reason_code = "coherence_check_failed"
        strategy = "clarify_and_restate"
        triggered = True
    elif state.quality_score and state.quality_score < 6.5:
        reason_code = "low_quality"
        strategy = "quality_retry_then_clarify"
        triggered = True

    fallback = {"triggered": triggered, "reason_code": reason_code, "strategy": strategy, "notes": []}

    if triggered and not state.prompt_injection_detected:
        questions = [
            "What exact deliverable should be produced first?",
            "Which constraint is non-negotiable for this response?",
        ][: state.request.max_questions]
        state.result.update(
            {
                "mode": "clarify",
                "recommended_questions": questions,
                "plan": [],
                "candidate_response": "Execution paused by ACA fallback manager. Clarify scope and constraints, then retry.",
            }
        )
        quality = _default_quality(state.result)
        quality.update({"safety": max(9, int(quality.get("safety", 9))), "overall": max(7.5, float(quality.get("overall", 7.5)))})
        notes = state.result.get("notes") if isinstance(state.result.get("notes"), list) else []
        notes.append(f"fallback:{reason_code}")
        state.result["notes"] = list(dict.fromkeys(notes))
        fallback["notes"].append("Returned clarify response due to deterministic guard failure.")

    state.fallback = fallback
    state.result["fallback"] = fallback
    _set_output(state, "M20", fallback.copy())
    _append_trace(state, module_id="M20", module_name="FallbackManager", tier="tier3_operational", status="fallback" if triggered else "pass", detail=f"Fallback {'triggered' if triggered else 'not_triggered'} ({reason_code}).")


def run_m21_aim_phase_2(state: ACAState) -> None:
    candidate = str(state.result.get("candidate_response") or "").strip()
    plan = state.result.get("plan") if isinstance(state.result.get("plan"), list) else []
    if not candidate and plan:
        state.result["candidate_response"] = "Structured response:\n" + "\n".join(f"{idx}. {step}" for idx, step in enumerate(plan, start=1))
    candidate = str(state.result.get("candidate_response") or "").strip()
    if state.result.get("mode") == "plan_execute" and plan and not candidate.startswith("1."):
        state.result["candidate_response"] = "Proposed execution path:\n" + "\n".join(f"{idx}. {str(step).strip()}" for idx, step in enumerate(plan, start=1))
        candidate = str(state.result.get("candidate_response") or "")
    _set_output(state, "M21", {"formatted": bool(candidate), "candidate_chars": len(candidate), "mode": state.result.get("mode", "clarify")})
    _append_trace(state, module_id="M21", module_name="AIMPhase2", tier="tier3_operational", status="adjusted" if candidate else "pass", detail="Output formatting pass completed.")


def run_m22_safety_alignment(state: ACAState) -> None:
    candidate = str(state.result.get("candidate_response") or "").strip()
    if candidate and not policies.output_is_safe(candidate):
        state.result = {
            "mode": "clarify",
            "ambiguity_score": 0.99,
            "recommended_questions": ["Please restate your request with a safe and lawful objective."],
            "plan": [],
            "candidate_response": "I cannot provide unsafe guidance. Please provide a safer request.",
            "quality": {
                "clarity": 9,
                "completeness": 8,
                "safety": 10,
                "format_compliance": 9,
                "overall": 9.0,
                "revision_required": False,
            },
            "iteration_count": 1,
            "notes": ["safety_alignment_override"],
            "fallback": {
                "triggered": True,
                "reason_code": "unsafe_output_detected",
                "strategy": "block_and_clarify",
                "notes": ["Unsafe output blocked by M22 safety layer."],
            },
        }
        state.safety = {
            "input_safe": not state.prompt_injection_detected,
            "output_safe": False,
            "blocked": True,
            "threat_level": "high",
            "module": "M22",
        }
        state.fallback = dict(state.result.get("fallback") or {})
        _set_output(state, "M22", state.safety.copy())
        _append_trace(state, module_id="M22", module_name="SafetyAlignment", tier="tier0_safety", status="blocked", detail="Unsafe output blocked and replaced with safe fallback.")
        return

    state.safety = {
        "input_safe": not state.prompt_injection_detected,
        "output_safe": True,
        "blocked": False,
        "threat_level": "low" if not state.prompt_injection_detected else "medium",
        "module": "M22",
    }
    _set_output(state, "M22", state.safety.copy())
    _append_trace(state, module_id="M22", module_name="SafetyAlignment", tier="tier0_safety", status="pass", detail="Output aligned with safety policy.")


def run_m23_interface_layer(state: ACAState) -> None:
    result = state.result if isinstance(state.result, dict) else {}
    result.setdefault("mode", "clarify")
    result.setdefault("ambiguity_score", 0.0)
    result.setdefault("recommended_questions", [])
    result.setdefault("plan", [])
    result.setdefault("candidate_response", "No assistant output was returned.")
    result.setdefault(
        "quality",
        {
            "clarity": 8,
            "completeness": 8,
            "safety": 9,
            "format_compliance": 8,
            "overall": 8.25,
            "revision_required": False,
        },
    )
    result.setdefault("iteration_count", 1)
    result.setdefault("notes", [])
    result.setdefault("model", state.request.model)
    result.setdefault("provider_mode", state.request.provider_mode)
    result["decision_graph"] = state.decision_graph
    result["module_outputs"] = state.module_outputs
    result["fallback"] = state.fallback or {"triggered": False, "reason_code": "none", "strategy": "none", "notes": []}
    result["safety"] = state.safety or {
        "input_safe": not state.prompt_injection_detected,
        "output_safe": True,
        "blocked": False,
        "threat_level": "low",
        "module": "M22",
    }
    result["aca_version"] = "4.1"
    result["final_message"] = str(result.get("candidate_response") or "").strip()
    _set_output(state, "M23", {"response_keys": sorted(result.keys()), "schema_family": "assistant_v1_plus_v2_fields"})
    result["module_outputs"] = state.module_outputs
    state.result = result
    _append_trace(state, module_id="M23", module_name="InterfaceLayer", tier="tier3_operational", status="pass", detail="Final interface payload normalized.")
