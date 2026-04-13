from __future__ import annotations

from typing import Dict

import numpy as np


class RallyQualityAnalyzer:
    def evaluate(self, state: Dict, tracker_diagnostics: Dict | None = None, motion_profile: Dict | None = None) -> Dict:
        tracker_diagnostics = tracker_diagnostics or {}
        motion_profile = motion_profile or {}

        signal_integrity = float(tracker_diagnostics.get("signal_integrity", 0.45) or 0.45)
        trajectory_quality = float(state.get("trajectory_quality", 0.45) or 0.45)
        referee_confidence = float(state.get("referee_confidence", 0.45) or 0.45)
        tactical_pressure = float(state.get("pressure_index", 0.45) or 0.45)
        motion_readiness = float(motion_profile.get("readiness_score", 0.45) or 0.45)

        interpretation_stability = float(np.clip(
            0.34 * trajectory_quality + 0.32 * referee_confidence + 0.2 * signal_integrity + 0.14 * motion_readiness,
            0.0,
            1.0,
        ))
        tactical_clarity = float(np.clip(
            0.38 * tactical_pressure + 0.24 * trajectory_quality + 0.2 * referee_confidence + 0.18 * motion_readiness,
            0.0,
            1.0,
        ))
        overall = float(np.clip(
            0.38 * interpretation_stability + 0.34 * tactical_clarity + 0.28 * signal_integrity,
            0.0,
            1.0,
        ))

        warnings = []
        if signal_integrity < 0.42:
            warnings.append("Trajectory signal is fragmented, so downstream reasoning may be less stable.")
        if referee_confidence < 0.4:
            warnings.append("Referee confidence is limited; outcome interpretation should be treated cautiously.")
        if motion_profile.get("quality_label") == "unavailable":
            warnings.append("Pose evidence is weak, so motion scoring is partially unavailable.")

        return {
            "signal_integrity": round(signal_integrity, 3),
            "interpretation_stability": round(interpretation_stability, 3),
            "tactical_clarity": round(tactical_clarity, 3),
            "overall_quality": round(overall, 3),
            "quality_label": self._label(overall),
            "warnings": warnings,
        }

    def _label(self, score: float) -> str:
        if score >= 0.8:
            return "excellent"
        if score >= 0.64:
            return "strong"
        if score >= 0.48:
            return "usable"
        if score >= 0.32:
            return "fragile"
        return "limited"
