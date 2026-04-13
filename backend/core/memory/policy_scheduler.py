from __future__ import annotations

from typing import Dict

import numpy as np


class PolicyScheduler:
    def schedule_retrieval(self, context: Dict, scenario_summary: Dict, metadata: Dict) -> Dict:
        familiarity = float(scenario_summary.get("familiarity", 0.0) or 0.0)
        success_rate = float(scenario_summary.get("success_rate", 0.5) or 0.5)
        rally_quality = float(context.get("rally_quality", 0.5) or 0.5)
        pressure_index = float(context.get("pressure_index", 0.5) or 0.5)
        attack_phase = context.get("attack_phase", "neutral")
        risk_level = metadata.get("risk_level", "medium")

        exploration_temperature = float(np.clip(0.9 - 0.42 * familiarity + 0.18 * (1.0 - rally_quality), 0.28, 1.05))
        exploitation_weight = float(np.clip(0.55 + 0.28 * familiarity + 0.12 * success_rate, 0.45, 1.0))
        pressure_alignment = self._pressure_alignment(attack_phase, pressure_index, metadata.get("tag"))
        risk_budget = self._risk_budget(attack_phase, rally_quality, risk_level)
        scheduler_bias = float(np.clip(
            0.06 * pressure_alignment + 0.04 * exploitation_weight - 0.05 * max(0.0, 0.55 - risk_budget),
            -0.08,
            0.12,
        ))

        return {
            "exploration_temperature": round(exploration_temperature, 3),
            "exploitation_weight": round(exploitation_weight, 3),
            "pressure_alignment": round(pressure_alignment, 3),
            "risk_budget": round(risk_budget, 3),
            "scheduler_bias": round(scheduler_bias, 3),
            "policy_mode": self._policy_mode(exploration_temperature, exploitation_weight),
        }

    def schedule_update(self, context: Dict, scenario_summary: Dict) -> Dict:
        familiarity = float(scenario_summary.get("familiarity", 0.0) or 0.0)
        success_rate = float(scenario_summary.get("success_rate", 0.5) or 0.5)
        rally_quality = float(context.get("rally_quality", 0.5) or 0.5)
        pressure_index = float(context.get("pressure_index", 0.5) or 0.5)

        learning_rate_scale = float(np.clip(0.72 + 0.22 * (1.0 - familiarity) + 0.16 * rally_quality, 0.65, 1.1))
        memory_stability = float(np.clip(0.48 + 0.42 * familiarity + 0.1 * success_rate, 0.4, 1.0))
        novelty_weight = float(np.clip(1.0 - familiarity + 0.15 * pressure_index, 0.15, 1.0))

        return {
            "learning_rate_scale": round(learning_rate_scale, 3),
            "memory_stability": round(memory_stability, 3),
            "novelty_weight": round(novelty_weight, 3),
        }

    def _pressure_alignment(self, attack_phase: str, pressure_index: float, tag: str | None) -> float:
        if attack_phase == "under_pressure":
            return 0.92 if tag in {"defense", "tactic"} else max(0.25, 0.55 - pressure_index * 0.2)
        if attack_phase == "advantage":
            return 0.92 if tag in {"attack", "net"} else 0.48
        if attack_phase == "transition":
            return 0.74 if tag in {"attack", "tactic"} else 0.58
        return 0.62

    def _risk_budget(self, attack_phase: str, rally_quality: float, risk_level: str) -> float:
        base = 0.78 if attack_phase == "advantage" else (0.42 if attack_phase == "under_pressure" else 0.58)
        quality_adjustment = 0.14 * rally_quality
        risk_penalty = {"low": 0.0, "medium": 0.08, "high": 0.18}.get(risk_level, 0.08)
        return float(np.clip(base + quality_adjustment - risk_penalty, 0.18, 1.0))

    def _policy_mode(self, exploration_temperature: float, exploitation_weight: float) -> str:
        if exploitation_weight >= 0.82 and exploration_temperature <= 0.45:
            return "exploit"
        if exploration_temperature >= 0.82:
            return "explore"
        return "balanced"
