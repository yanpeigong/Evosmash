from __future__ import annotations

from collections import Counter
from typing import Dict, List

import numpy as np


class RetrievalReranker:
    def rerank(self, candidates: List[Dict], context: Dict | None = None, scenario_summary: Dict | None = None, top_k: int | None = None) -> List[Dict]:
        context = context or {}
        scenario_summary = scenario_summary or {}
        if not candidates:
            return []

        family_counter = Counter(
            (candidate.get("metadata", {}) or {}).get("style_family", "balanced")
            for candidate in candidates
        )
        phase_counter = Counter(
            (candidate.get("metadata", {}) or {}).get("phase_preference", "neutral")
            for candidate in candidates
        )

        reranked = []
        for candidate in candidates:
            metadata = candidate.get("metadata", {}) or {}
            continuity_score = self._continuity_score(context, metadata, candidate)
            coverage_score = self._coverage_score(context, metadata, scenario_summary)
            volatility_guard = self._volatility_guard(context, candidate, metadata)
            novelty_bonus = self._novelty_bonus(metadata, family_counter, phase_counter, scenario_summary)
            rerank_score = float(np.clip(
                0.48 * float(candidate.get("score", 0.0) or 0.0)
                + 0.16 * float(candidate.get("context_score", 0.0) or 0.0)
                + 0.12 * continuity_score
                + 0.11 * coverage_score
                + 0.09 * volatility_guard
                + novelty_bonus,
                0.0,
                1.65,
            ))
            rank_reason = self._build_rank_reason(
                metadata=metadata,
                candidate=candidate,
                continuity_score=continuity_score,
                coverage_score=coverage_score,
                volatility_guard=volatility_guard,
                scenario_summary=scenario_summary,
            )
            frontier_hint = self._frontier_hint(metadata, context, scenario_summary, volatility_guard)
            reranked.append(
                {
                    **candidate,
                    "rerank_score": round(rerank_score, 3),
                    "continuity_score": round(continuity_score, 3),
                    "coverage_score": round(coverage_score, 3),
                    "volatility_guard": round(volatility_guard, 3),
                    "novelty_bonus": round(novelty_bonus, 3),
                    "rank_reason": rank_reason,
                    "frontier_hint": frontier_hint,
                }
            )

        reranked.sort(
            key=lambda item: (
                item.get("rerank_score", 0.0),
                item.get("score", 0.0),
                item.get("expected_win_rate", 0.0),
            ),
            reverse=True,
        )
        return reranked[:top_k] if top_k else reranked

    def _continuity_score(self, context: Dict, metadata: Dict, candidate: Dict) -> float:
        phase_fit = 1.0 if context.get("attack_phase") == metadata.get("phase_preference") else 0.58
        tempo_fit = self._tempo_fit(context.get("tempo_profile", "medium"), metadata.get("tempo_band", "medium"))
        hitter_fit = 1.0 if metadata.get("preferred_last_hitter", "UNKNOWN") in {"UNKNOWN", context.get("last_hitter", "UNKNOWN")} else 0.42
        graph_bias = min(float(candidate.get("graph_bias", 0.0) or 0.0) * 10.0, 1.0)
        scheduler_profile = candidate.get("scheduler_profile", {}) or {}
        scheduler_mode = scheduler_profile.get("policy_mode", "balanced")
        scheduler_fit = 0.92 if scheduler_mode == "exploit" else (0.82 if scheduler_mode == "balanced" else 0.66)
        return float(np.clip(0.34 * phase_fit + 0.24 * tempo_fit + 0.18 * hitter_fit + 0.12 * graph_bias + 0.12 * scheduler_fit, 0.0, 1.0))

    def _coverage_score(self, context: Dict, metadata: Dict, scenario_summary: Dict) -> float:
        familiarity = float(scenario_summary.get("familiarity", 0.0) or 0.0)
        success_rate = float(scenario_summary.get("success_rate", 0.5) or 0.5)
        preferred_tactics = scenario_summary.get("preferred_tactics", {}) or {}
        tactic_id = metadata.get("tactic_id")
        preference_score = 1.0 if preferred_tactics.get(tactic_id, 0) else 0.42
        attack_phase = context.get("attack_phase", "neutral")
        risk_level = metadata.get("risk_level", "medium")
        risk_budget = 0.85 if attack_phase == "advantage" else (0.42 if attack_phase == "under_pressure" else 0.62)
        risk_fit = 1.0
        if risk_level == "high" and risk_budget < 0.55:
            risk_fit = 0.35
        elif risk_level == "medium" and risk_budget < 0.45:
            risk_fit = 0.6
        return float(np.clip(0.32 * (0.45 + 0.55 * success_rate) + 0.28 * preference_score + 0.24 * risk_fit + 0.16 * (1.0 - 0.45 * familiarity), 0.0, 1.0))

    def _volatility_guard(self, context: Dict, candidate: Dict, metadata: Dict) -> float:
        risk_level = metadata.get("risk_level", "medium")
        rally_quality = float(context.get("rally_quality", 0.5) or 0.5)
        pressure_index = float(context.get("pressure_index", 0.5) or 0.5)
        confidence = float(candidate.get("expected_win_rate", 50.0) or 50.0) / 100.0
        if risk_level == "high":
            risk_suppression = 0.38
        elif risk_level == "medium":
            risk_suppression = 0.62
        else:
            risk_suppression = 0.84
        guard = 0.36 * risk_suppression + 0.32 * rally_quality + 0.18 * confidence + 0.14 * (1.0 - max(0.0, pressure_index - 0.45))
        return float(np.clip(guard, 0.0, 1.0))

    def _novelty_bonus(self, metadata: Dict, family_counter: Counter, phase_counter: Counter, scenario_summary: Dict) -> float:
        familiarity = float(scenario_summary.get("familiarity", 0.0) or 0.0)
        style_family = metadata.get("style_family", "balanced")
        phase_preference = metadata.get("phase_preference", "neutral")
        family_frequency = family_counter.get(style_family, 1)
        phase_frequency = phase_counter.get(phase_preference, 1)
        rarity = min(1.0 / family_frequency + 0.8 / phase_frequency, 1.4)
        exploration_window = max(0.0, 1.0 - familiarity)
        return float(np.clip(0.05 * rarity * exploration_window, -0.02, 0.08))

    def _tempo_fit(self, current_tempo: str, preferred_tempo: str) -> float:
        if current_tempo == preferred_tempo:
            return 1.0
        if {current_tempo, preferred_tempo} <= {"medium", "medium-fast", "controlled"}:
            return 0.76
        if {current_tempo, preferred_tempo} <= {"fast", "medium-fast"}:
            return 0.72
        return 0.38

    def _build_rank_reason(
        self,
        metadata: Dict,
        candidate: Dict,
        continuity_score: float,
        coverage_score: float,
        volatility_guard: float,
        scenario_summary: Dict,
    ) -> str:
        tactic_name = candidate.get("name", metadata.get("name", "This tactic"))
        policy_mode = (candidate.get("scheduler_profile", {}) or {}).get("policy_mode", "balanced")
        familiarity = float(scenario_summary.get("familiarity", 0.0) or 0.0)
        return (
            f"{tactic_name} stayed near the top because continuity scored {continuity_score:.2f}, coverage scored {coverage_score:.2f}, "
            f"and the volatility guard held at {volatility_guard:.2f}. Policy mode is {policy_mode} with scenario familiarity {familiarity:.2f}."
        )

    def _frontier_hint(self, metadata: Dict, context: Dict, scenario_summary: Dict, volatility_guard: float) -> str:
        familiarity = float(scenario_summary.get("familiarity", 0.0) or 0.0)
        attack_phase = context.get("attack_phase", "neutral").replace("_", " ")
        style_family = metadata.get("style_family", "balanced").replace("-", " ")
        if familiarity < 0.25:
            return f"Use this as an exploratory {style_family} branch while the {attack_phase} scenario is still under-sampled."
        if volatility_guard < 0.55:
            return f"Keep this branch on a short leash in {attack_phase} exchanges because the volatility guard is still fragile."
        return f"This {style_family} branch is stable enough to keep reinforcing in {attack_phase} exchanges."
