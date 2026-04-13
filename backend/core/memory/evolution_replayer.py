from __future__ import annotations

from typing import Dict, List

import numpy as np


class TacticEvolutionReplayer:
    def build_candidate_replays(self, candidates: List[Dict], context: Dict | None = None, scenario_summary: Dict | None = None) -> List[Dict]:
        context = context or {}
        scenario_summary = scenario_summary or {}
        if not candidates:
            return []

        enriched = []
        frontier_summary = self._frontier_summary(candidates, scenario_summary)
        for index, candidate in enumerate(candidates, start=1):
            replay = self._candidate_replay(index, candidate, context, scenario_summary, frontier_summary)
            enriched.append(
                {
                    **candidate,
                    "evolution_replay": replay,
                    "frontier_hint": replay.get("frontier_hint", candidate.get("frontier_hint", "")),
                }
            )
        return enriched

    def summarize_update(self, tactic_id: str, reward: float, update_payload: Dict | None = None, context: Dict | None = None, tactic_name: str | None = None) -> Dict:
        update_payload = update_payload or {}
        context = context or {}
        scheduler_profile = update_payload.get("scheduler_profile", {}) or {}
        scenario_summary = update_payload.get("scenario_summary", {}) or {}
        weighted_increment = float(update_payload.get("weighted_increment", 0.0) or 0.0)
        certainty_weight = float(update_payload.get("certainty_weight", 0.5) or 0.5)
        adaptation_level = update_payload.get("adaptation_level", "moderate")
        policy_mode = scheduler_profile.get("memory_stability", 0.5)
        direction = "reinforce" if reward >= 0 else "cooldown"
        tactic_label = tactic_name or tactic_id

        replay_score = float(np.clip(
            0.32 * certainty_weight
            + 0.24 * min(abs(reward) / 10.0, 1.0)
            + 0.22 * float(scheduler_profile.get("learning_rate_scale", 1.0) or 1.0)
            + 0.22 * float(scenario_summary.get("familiarity", 0.0) or 0.0),
            0.0,
            1.25,
        ))
        summary = (
            f"{tactic_label} entered a {direction} cycle with weighted increment {weighted_increment:.2f}, "
            f"certainty weight {certainty_weight:.2f}, and adaptation level {adaptation_level}."
        )

        return {
            "tactic_id": tactic_id,
            "tactic_name": tactic_label,
            "direction": direction,
            "reward": round(float(reward or 0.0), 3),
            "replay_score": round(replay_score, 3),
            "adaptation_level": adaptation_level,
            "stability_reference": round(float(policy_mode or 0.0), 3),
            "scenario_familiarity": round(float(scenario_summary.get("familiarity", 0.0) or 0.0), 3),
            "upgrade_path": self._update_upgrade_path(context, update_payload),
            "summary": summary,
        }

    def _candidate_replay(
        self,
        rank: int,
        candidate: Dict,
        context: Dict,
        scenario_summary: Dict,
        frontier_summary: Dict,
    ) -> Dict:
        metadata = candidate.get("metadata", {}) or {}
        policy_mode = (candidate.get("scheduler_profile", {}) or {}).get("policy_mode", "balanced")
        risk_level = metadata.get("risk_level", "medium")
        style_family = metadata.get("style_family", "balanced")
        score = float(candidate.get("rerank_score", candidate.get("score", 0.0)) or 0.0)
        familiarity = float(scenario_summary.get("familiarity", 0.0) or 0.0)
        continuity = float(candidate.get("continuity_score", 0.5) or 0.5)
        coverage = float(candidate.get("coverage_score", 0.5) or 0.5)
        replay_score = float(np.clip(0.42 * score + 0.26 * continuity + 0.18 * coverage + 0.14 * (1.0 - 0.45 * familiarity), 0.0, 1.45))
        development_stage = self._development_stage(rank, policy_mode, familiarity, replay_score)
        training_block = self._training_block(context, risk_level, style_family)
        frontier_hint = self._frontier_hint(rank, development_stage, frontier_summary, risk_level)

        return {
            "development_stage": development_stage,
            "policy_mode": policy_mode,
            "replay_score": round(replay_score, 3),
            "risk_axis": risk_level,
            "training_block": training_block,
            "why_now": self._why_now(candidate, context, familiarity),
            "upgrade_path": self._candidate_upgrade_path(candidate, context, policy_mode),
            "frontier_hint": frontier_hint,
        }

    def _frontier_summary(self, candidates: List[Dict], scenario_summary: Dict) -> Dict:
        if not candidates:
            return {"frontier_shape": "empty", "stability_gap": 0.0}
        top_score = float(candidates[0].get("rerank_score", candidates[0].get("score", 0.0)) or 0.0)
        third_score = float(candidates[min(2, len(candidates) - 1)].get("rerank_score", candidates[min(2, len(candidates) - 1)].get("score", 0.0)) or 0.0)
        stability_gap = float(np.clip(top_score - third_score, 0.0, 1.0))
        familiarity = float(scenario_summary.get("familiarity", 0.0) or 0.0)
        if stability_gap >= 0.28:
            frontier_shape = "sharp"
        elif familiarity < 0.3:
            frontier_shape = "open"
        else:
            frontier_shape = "layered"
        return {
            "frontier_shape": frontier_shape,
            "stability_gap": round(stability_gap, 3),
        }

    def _development_stage(self, rank: int, policy_mode: str, familiarity: float, replay_score: float) -> str:
        if rank == 1 and replay_score >= 0.95 and policy_mode == "exploit":
            return "weaponize"
        if familiarity < 0.28:
            return "probe"
        if replay_score >= 0.78:
            return "refine"
        return "stabilize"

    def _training_block(self, context: Dict, risk_level: str, style_family: str) -> str:
        attack_phase = context.get("attack_phase", "neutral")
        if attack_phase == "under_pressure":
            return "pressure absorb + counter release"
        if risk_level == "high":
            return f"early preparation for {style_family} commitment"
        if attack_phase == "advantage":
            return "finish the rally on the first clean window"
        return "tempo control and shape preservation"

    def _why_now(self, candidate: Dict, context: Dict, familiarity: float) -> str:
        tactic_name = candidate.get("name", "This tactic")
        phase = context.get("attack_phase", "neutral").replace("_", " ")
        score = float(candidate.get("rerank_score", candidate.get("score", 0.0)) or 0.0)
        if familiarity < 0.25:
            return f"{tactic_name} is worth probing now because the {phase} branch is still under-learned and the current score is {score:.2f}."
        return f"{tactic_name} is relevant now because it preserved strong rank value at {score:.2f} in a {phase} exchange."

    def _candidate_upgrade_path(self, candidate: Dict, context: Dict, policy_mode: str) -> List[str]:
        phase = context.get("attack_phase", "neutral").replace("_", " ")
        tactic_name = candidate.get("name", "This tactic")
        steps = [
            f"Rehearse {tactic_name} entries from {phase} situations.",
            "Track whether the first attacking touch creates space or panic.",
        ]
        if policy_mode == "explore":
            steps.append("Keep the sample size broad before narrowing into a fixed preference.")
        else:
            steps.append("Reinforce the most repeatable variation and trim noisy branches.")
        return steps

    def _frontier_hint(self, rank: int, development_stage: str, frontier_summary: Dict, risk_level: str) -> str:
        frontier_shape = frontier_summary.get("frontier_shape", "layered")
        if development_stage == "weaponize":
            return f"Frontier is {frontier_shape}; this branch can be hardened into a primary scoring pattern."
        if risk_level == "high":
            return f"Frontier is {frontier_shape}; keep this branch as a selective weapon rather than a default habit."
        if rank > 1:
            return f"Frontier is {frontier_shape}; keep this branch alive as a secondary lane for variation."
        return f"Frontier is {frontier_shape}; continue refining this branch before expanding sideways."

    def _update_upgrade_path(self, context: Dict, update_payload: Dict) -> List[str]:
        reason = update_payload.get("policy_update_reason", "")
        strategy_tag = update_payload.get("strategy_tag", "adapt")
        phase = context.get("attack_phase", "neutral").replace("_", " ")
        return [
            f"Use {strategy_tag} as the next adjustment frame for {phase} rallies.",
            reason or "Preserve only the stable branch of the tactic after this update.",
            "Re-check whether the tactic still fits the same court context after the next few rallies.",
        ]
