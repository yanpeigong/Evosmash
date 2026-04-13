from __future__ import annotations

from typing import Dict

import numpy as np


class ConfidenceCalibrator:
    def calibrate(self, state: Dict, tracker_diagnostics: Dict | None = None, motion_profile: Dict | None = None, rally_quality: Dict | None = None) -> Dict:
        tracker_diagnostics = tracker_diagnostics or {}
        motion_profile = motion_profile or {}
        rally_quality = rally_quality or {}

        referee_confidence = float(state.get("referee_confidence", 0.5) or 0.5)
        trajectory_quality = float(state.get("trajectory_quality", 0.5) or 0.5)
        tracker_integrity = float(tracker_diagnostics.get("signal_integrity", 0.5) or 0.5)
        motion_readiness = float(motion_profile.get("readiness_score", 0.45) or 0.45)
        rally_stability = float(rally_quality.get("interpretation_stability", 0.5) or 0.5)
        pressure_index = float(state.get("pressure_index", 0.5) or 0.5)

        calibrated_confidence = float(np.clip(
            0.26 * referee_confidence + 0.22 * trajectory_quality + 0.18 * tracker_integrity + 0.14 * motion_readiness + 0.2 * rally_stability,
            0.0,
            1.0,
        ))
        volatility = float(np.clip(
            0.38 * abs(referee_confidence - trajectory_quality) + 0.34 * (1.0 - tracker_integrity) + 0.28 * max(0.0, pressure_index - 0.55),
            0.0,
            1.0,
        ))
        caution_level = self._caution_level(calibrated_confidence, volatility)

        return {
            "calibrated_confidence": round(calibrated_confidence, 3),
            "volatility": round(volatility, 3),
            "caution_level": caution_level,
            "confidence_summary": self._summary(calibrated_confidence, volatility, caution_level),
        }

    def _caution_level(self, calibrated_confidence: float, volatility: float) -> str:
        if calibrated_confidence < 0.42 or volatility > 0.62:
            return "high"
        if calibrated_confidence < 0.62 or volatility > 0.38:
            return "medium"
        return "low"

    def _summary(self, confidence: float, volatility: float, caution_level: str) -> str:
        return (
            f"Calibrated confidence is {confidence:.2f} with volatility {volatility:.2f}; "
            f"recommended caution level is {caution_level}."
        )
