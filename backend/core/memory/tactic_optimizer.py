from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict

import numpy as np


RISK_WEIGHT = {
    "low": 0.15,
    "medium": 0.45,
    "high": 0.8,
}


@dataclass
class RetrievalContextProfile:
    event: str
    speed: float
    match_type: str
    court_context: str
    auto_result: str
    trajectory_quality: float
    referee_confidence: float
    attack_phase: str
    tempo_profile: str
    last_hitter: str
    pressure_index: float


class TacticOptimizer:
    def build_context_profile(self, context: Dict) -> RetrievalContextProfile:
        return RetrievalContextProfile(
            event=context.get("event") or "Unknown",
            speed=float(context.get("max_speed_kmh", 0.0) or 0.0),
            match_type=context.get("match_type") or "singles",
            court_context=context.get("court_context") or "unknown",
            auto_result=context.get("auto_result") or "UNKNOWN",
            trajectory_quality=float(context.get("trajectory_quality", 0.5) or 0.5),
            referee_confidence=float(context.get("referee_confidence", 0.5) or 0.5),
            attack_phase=context.get("attack_phase") or "neutral",
            tempo_profile=context.get("tempo_profile") or "medium",
            last_hitter=context.get("last_hitter") or "UNKNOWN",
            pressure_index=float(context.get("pressure_index", 0.5) or 0.5),
        )

    def score_candidate(self, metadata: Dict, semantic_score: float, bayesian_score: float, context: Dict) -> Dict:
        profile = self.build_context_profile(context)
        event_fit = 1.0 if profile.event in metadata.get("applicable_events", []) else 0.2
        match_fit = 1.0 if profile.match_type in metadata.get("preferred_match_types", []) else 0.35
        speed_fit = self._speed_fit(profile.speed, metadata)
        court_fit = self._court_fit(profile.court_context, metadata)
        phase_fit = self._phase_fit(profile.attack_phase, metadata.get("phase_preference"))
        tempo_fit = self._tempo_fit(profile.tempo_profile, metadata.get("tempo_band"))
        hitter_fit = self._hitter_fit(profile.last_hitter, metadata.get("preferred_last_hitter"))
        tactical_fit = float(np.clip(
            0.22 * event_fit + 0.16 * match_fit + 0.16 * speed_fit + 0.14 * court_fit + 0.16 * phase_fit + 0.08 * tempo_fit + 0.08 * hitter_fit,
            0.0,
            1.0,
        ))

        confidence_blend = float(np.clip(0.55 * profile.trajectory_quality + 0.45 * profile.referee_confidence, 0.0, 1.0))
        quality_weight = float(np.clip(0.68 + 0.22 * profile.trajectory_quality + 0.1 * profile.referee_confidence, 0.68, 1.08))
        exploration_bonus = self._exploration_bonus(metadata)
        pressure_bonus = self._pressure_bonus(profile, metadata)
        risk_penalty = self._risk_penalty(profile, metadata)
        stability_bonus = 0.06 if confidence_blend >= 0.78 else (0.03 if confidence_blend >= 0.6 else 0.0)

        final_score = quality_weight * (
            0.28 * semantic_score + 0.3 * bayesian_score + 0.42 * tactical_fit
        ) + exploration_bonus + pressure_bonus + stability_bonus - risk_penalty
        final_score = float(np.clip(final_score, 0.0, 1.25))

        return {
            "final_score": final_score,
            "quality_weight": round(quality_weight, 3),
            "context_score": round(tactical_fit, 3),
            "exploration_bonus": round(exploration_bonus, 3),
            "pressure_bonus": round(pressure_bonus, 3),
            "risk_penalty": round(risk_penalty, 3),
            "stability_bonus": round(stability_bonus, 3),
            "fit_breakdown": {
                "event_fit": round(event_fit, 3),
                "match_fit": round(match_fit, 3),
                "speed_fit": round(speed_fit, 3),
                "court_fit": round(court_fit, 3),
                "phase_fit": round(phase_fit, 3),
                "tempo_fit": round(tempo_fit, 3),
                "hitter_fit": round(hitter_fit, 3),
            },
            "selection_profile": asdict(profile),
        }

    def build_update_plan(self, metadata: Dict, reward: float, context: Dict) -> Dict:
        profile = self.build_context_profile(context)
        matches = float(metadata.get("matches", 0) or 0)
        alpha = float(metadata.get("alpha", 1.0) or 1.0)
        beta_val = float(metadata.get("beta", 1.0) or 1.0)
        trajectory_quality = profile.trajectory_quality
        referee_confidence = profile.referee_confidence
        retrieval_confidence = float(context.get("retrieval_confidence", 0.5) or 0.5)
        contextual_fit = float(context.get("context_score", 0.5) or 0.5)
        risk_penalty = self._risk_penalty(profile, metadata)

        certainty_weight = float(np.clip(0.25 + 0.4 * trajectory_quality + 0.35 * referee_confidence, 0.25, 1.0))
        retrieval_weight = float(np.clip(0.35 + 0.65 * retrieval_confidence, 0.35, 1.0))
        contextual_weight = float(np.clip(0.4 + 0.6 * contextual_fit, 0.4, 1.0))
        adaptation_temperature = 1.0 if matches < 4 else (0.82 if matches < 10 else 0.68)
        risk_guard = float(np.clip(1.0 - 0.5 * risk_penalty, 0.55, 1.0))

        effective_weight = certainty_weight * retrieval_weight * contextual_weight * adaptation_temperature * risk_guard
        positive_delta = min(max(reward, 0.0) / 10.0 * effective_weight, 1.15)
        negative_delta = min(abs(min(reward, 0.0)) / 5.0 * effective_weight, 1.15)

        if reward >= 0:
            alpha += positive_delta
            strategy_tag = "reinforce-success"
            weighted_increment = positive_delta
            delta_target = "alpha"
        else:
            beta_val += negative_delta
            strategy_tag = "cooldown-risk"
            weighted_increment = negative_delta
            delta_target = "beta"

        if alpha + beta_val > 60:
            alpha *= 0.96
            beta_val *= 0.96

        adaptation_level = "strong" if effective_weight >= 0.82 else ("moderate" if effective_weight >= 0.58 else "conservative")
        reason = (
            f"Updated {delta_target} with certainty {certainty_weight:.2f}, retrieval {retrieval_weight:.2f}, "
            f"context {contextual_weight:.2f}, adaptation temperature {adaptation_temperature:.2f}, and risk guard {risk_guard:.2f}."
        )

        return {
            "alpha": alpha,
            "beta": beta_val,
            "matches": int(matches + 1),
            "weighted_increment": round(weighted_increment, 3),
            "certainty_weight": round(certainty_weight, 3),
            "retrieval_weight": round(retrieval_weight, 3),
            "contextual_weight": round(contextual_weight, 3),
            "adaptation_temperature": round(adaptation_temperature, 3),
            "risk_guard": round(risk_guard, 3),
            "adaptation_level": adaptation_level,
            "strategy_tag": strategy_tag,
            "policy_update_reason": reason,
            "reward_components": {
                "raw_reward": reward,
                "trajectory_quality": round(trajectory_quality, 3),
                "referee_confidence": round(referee_confidence, 3),
                "retrieval_confidence": round(retrieval_confidence, 3),
                "context_score": round(contextual_fit, 3),
            },
        }

    def _speed_fit(self, speed: float, metadata: Dict) -> float:
        lower = float(metadata.get("speed_min", 0.0) or 0.0)
        upper = float(metadata.get("speed_max", 999.0) or 999.0)
        if lower <= speed <= upper:
            return 1.0
        distance = min(abs(speed - lower), abs(speed - upper))
        return float(np.clip(1.0 - distance / 120.0, 0.15, 0.92))

    def _court_fit(self, court_context: str, metadata: Dict) -> float:
        options = metadata.get("court_contexts", []) or []
        if not options:
            return 0.5
        if court_context in options:
            return 1.0
        depth = (court_context or "").split("_")[0]
        if any(option.startswith(depth) for option in options if isinstance(option, str)):
            return 0.72
        return 0.28

    def _phase_fit(self, phase: str, preferred: str) -> float:
        if not preferred or preferred == phase:
            return 1.0
        compatible = {
            "advantage": {"transition"},
            "transition": {"advantage", "neutral"},
            "under_pressure": {"neutral"},
            "neutral": {"transition", "under_pressure"},
        }
        if phase in compatible and preferred in compatible[phase]:
            return 0.72
        return 0.3

    def _tempo_fit(self, tempo: str, preferred: str) -> float:
        if not preferred or tempo == preferred:
            return 1.0
        if {tempo, preferred} <= {"medium", "medium-fast", "controlled"}:
            return 0.74
        if {tempo, preferred} <= {"fast", "medium-fast"}:
            return 0.78
        return 0.35

    def _hitter_fit(self, last_hitter: str, preferred: str) -> float:
        if not preferred or preferred == "UNKNOWN":
            return 0.5
        return 1.0 if last_hitter == preferred else 0.3

    def _pressure_bonus(self, profile: RetrievalContextProfile, metadata: Dict) -> float:
        pressure_gain = float(metadata.get("pressure_gain", 0.5) or 0.5)
        if profile.attack_phase == "under_pressure":
            return 0.08 * pressure_gain if metadata.get("tag") in {"defense", "tactic"} else 0.02 * pressure_gain
        if profile.attack_phase == "advantage":
            return 0.08 * pressure_gain if metadata.get("tag") in {"attack", "net"} else 0.03 * pressure_gain
        if profile.pressure_index > 0.72:
            return 0.05 * pressure_gain
        return 0.0

    def _risk_penalty(self, profile: RetrievalContextProfile, metadata: Dict) -> float:
        risk_level = metadata.get("risk_level", "medium")
        baseline = RISK_WEIGHT.get(risk_level, 0.45)
        if profile.attack_phase == "advantage":
            baseline *= 0.6
        elif profile.attack_phase == "under_pressure":
            baseline *= 1.18
        confidence = 0.5 * profile.trajectory_quality + 0.5 * profile.referee_confidence
        return float(np.clip((1.0 - confidence) * baseline * 0.18, 0.0, 0.16))

    def _exploration_bonus(self, metadata: Dict) -> float:
        matches = float(metadata.get("matches", 0) or 0)
        if matches < 2:
            return 0.1
        if matches < 5:
            return 0.05
        if matches < 8:
            return 0.02
        return 0.0
