from __future__ import annotations

from collections import Counter
from typing import Dict, List

import numpy as np


class MatchIntelligenceAnalyzer:
    def summarize(self, timeline: List[Dict], match_type: str, sequence_context: Dict | None = None, duel_summary: Dict | None = None) -> Dict:
        sequence_context = sequence_context or {}
        duel_summary = duel_summary or {}
        if not timeline:
            return {
                "match_type": match_type,
                "dominant_pattern": "unavailable",
                "momentum_state": "neutral",
                "tactical_identity": "unavailable",
                "confidence_trend": "flat",
                "pressure_profile": {},
                "event_distribution": {},
                "tactic_distribution": {},
                "recommended_focus": [],
                "sequence_memory": sequence_context,
                "duel_summary": duel_summary,
            }

        events = [item.get("physics", {}).get("event", "Unknown") for item in timeline]
        results = [item.get("auto_result", "UNKNOWN") for item in timeline]
        pressure_values = [float(item.get("physics", {}).get("pressure_index", 0.0) or 0.0) for item in timeline]
        confidence_values = [float(item.get("physics", {}).get("referee_confidence", 0.0) or 0.0) for item in timeline]
        tactic_names = [
            item.get("tactics", [{}])[0].get("name", "None")
            for item in timeline
            if item.get("tactics")
        ]

        event_distribution = dict(Counter(events))
        tactic_distribution = dict(Counter(tactic_names))
        dominant_pattern = max(event_distribution, key=event_distribution.get) if event_distribution else "Unknown"
        tactical_identity = max(tactic_distribution, key=tactic_distribution.get) if tactic_distribution else "Adaptive"
        win_count = sum(1 for result in results if result == "WIN")
        loss_count = sum(1 for result in results if result == "LOSS")
        momentum_state = self._momentum_state(results)
        confidence_trend = self._confidence_trend(confidence_values)
        pressure_profile = {
            "mean_pressure": round(float(np.mean(pressure_values)) if pressure_values else 0.0, 3),
            "max_pressure": round(float(np.max(pressure_values)) if pressure_values else 0.0, 3),
            "pressure_volatility": round(float(np.std(pressure_values)) if pressure_values else 0.0, 3),
        }

        recommended_focus = self._recommended_focus(
            dominant_pattern=dominant_pattern,
            tactical_identity=tactical_identity,
            momentum_state=momentum_state,
            mean_pressure=pressure_profile["mean_pressure"],
            win_count=win_count,
            loss_count=loss_count,
            sequence_context=sequence_context,
            duel_summary=duel_summary,
        )

        return {
            "match_type": match_type,
            "dominant_pattern": dominant_pattern,
            "momentum_state": momentum_state,
            "tactical_identity": tactical_identity,
            "confidence_trend": confidence_trend,
            "pressure_profile": pressure_profile,
            "event_distribution": event_distribution,
            "tactic_distribution": tactic_distribution,
            "recommended_focus": recommended_focus,
            "win_loss_balance": {
                "wins": win_count,
                "losses": loss_count,
            },
            "sequence_memory": sequence_context,
            "duel_summary": duel_summary,
            "adaptation_score": round(float(sequence_context.get("adaptation_score", 0.0) or 0.0), 3),
        }

    def _momentum_state(self, results: List[str]) -> str:
        if not results:
            return "neutral"
        score = 0
        for index, result in enumerate(results[-4:], start=1):
            if result == "WIN":
                score += index
            elif result == "LOSS":
                score -= index
        if score >= 4:
            return "surging"
        if score <= -4:
            return "under-pressure"
        return "neutral"

    def _confidence_trend(self, values: List[float]) -> str:
        if len(values) < 2:
            return "flat"
        first_half = float(np.mean(values[: max(1, len(values) // 2)]))
        second_half = float(np.mean(values[max(1, len(values) // 2) :]))
        diff = second_half - first_half
        if diff >= 0.08:
            return "rising"
        if diff <= -0.08:
            return "falling"
        return "flat"

    def _recommended_focus(
        self,
        dominant_pattern: str,
        tactical_identity: str,
        momentum_state: str,
        mean_pressure: float,
        win_count: int,
        loss_count: int,
        sequence_context: Dict,
        duel_summary: Dict,
    ) -> List[str]:
        focus = []
        if mean_pressure >= 0.62:
            focus.append("stabilize-pressure-management")
        if dominant_pattern in {"Drive Exchange", "Fast Flat Exchange"}:
            focus.append("improve-flat-exchange-control")
        if tactical_identity in {"Counter Block", "Straight Relief Clear"}:
            focus.append("build-transition-defense")
        if momentum_state == "under-pressure" or loss_count > win_count:
            focus.append("recover-rally-initiative")
        if momentum_state == "surging":
            focus.append("convert-advantage-more-efficiently")
        if float(sequence_context.get("adaptation_score", 0.0) or 0.0) >= 0.62:
            focus.append("consolidate-recent-adaptations")
        if duel_summary.get("dominant_duel") and duel_summary.get("dominant_duel") != "unavailable":
            focus.append("prepare-for-recurring-counter-duels")
        if not focus:
            focus.append("maintain-balanced-decision-making")
        return focus
