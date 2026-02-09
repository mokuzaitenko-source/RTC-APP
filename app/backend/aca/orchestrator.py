from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

from app.backend.aca import modules
from app.backend.aca.trace import serialize_trace
from app.backend.aca.types import ACARequest, ACAState


BuildResultFn = Callable[..., Dict[str, object]]


@dataclass
class ACAOrchestratorHooks:
	build_result: BuildResultFn


class ACAOrchestrator:
	def __init__(self, hooks: ACAOrchestratorHooks):
		self._hooks = hooks

	def run(self, request: ACARequest) -> Tuple[Dict[str, object], List[dict]]:
		state = ACAState(request=request)

		modules.run_m0_safety_memory_guard(state)
		modules.run_m1_identity_gate(state)
		modules.run_m2_preference_loader(state)
		modules.run_m3_meta_controller(state)
		modules.run_m4_mode_system(state)
		modules.run_m5_path_selector(state)
		modules.run_m6_lands_mixer(state)
		modules.run_m7_emotional_regulation(state)
		modules.run_m8_bottleneck_monitor(state)
		modules.run_m9_sparse_attention_dsa(state)
		modules.run_m10_process_engine(state)
		modules.run_m11_decision_tree_builder(state)
		modules.run_m12_aim_phase_1(state)
		modules.run_m13_eve_supra_clean(state)
		modules.run_m14_eve_core(state, self._hooks.build_result)
		modules.run_m15_seed_scoring(state)
		modules.run_m16_refinement_loop(state)
		modules.run_m17_conflict_resolution(state)
		modules.run_m18_task_integrity(state)
		modules.run_m19_error_coherence(state)
		modules.run_m20_fallback_manager(state)
		modules.run_m21_aim_phase_2(state)
		modules.run_m22_safety_alignment(state)
		modules.run_m23_interface_layer(state)

		return state.result, serialize_trace(state.trace)
