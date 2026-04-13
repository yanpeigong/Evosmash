from __future__ import annotations

from typing import Dict, List

import numpy as np


class RefereeAuditTrail:
    def audit(
        self,
        state: Dict,
        tracker_diagnostics: Dict | None = None,
        motion_profile: Dict | None = None,
        rally_quality: Dict | None = None,
        confidence_report: Dict | None = None,
    ) -> Dict:
        tracker_diagnostics = tracker_diagnostics or {}
        motion_profile = motion_profile or {}
        rally_quality = rally_quality or {}
        confidence_report = confidence_report or {}

        contradictions = self._collect_contradictions(state, tracker_diagnostics, rally_quality, confidence_report)
        support_signals = self._collect_support_signals(state, tracker_diagnostics, motion_profile, confidence_report)

        referee_confidence = float(state.get("referee_confidence", 0.5) or 0.5)
        landing_confidence = float(state.get("landing_confidence", 0.5) or 0.5)
        direction_consistency = float(state.get("direction_consistency", 0.5) or 0.5)
        calibrated_confidence = float(confidence_report.get("calibrated_confidence", 0.5) or 0.5)
        volatility = float(confidence_report.get("volatility", 0.0) or 0.0)
        signal_integrity = float(tracker_diagnostics.get("signal_integrity", 0.5) or 0.5)
        interpretation_stability = float(rally_quality.get("interpretation_stability", 0.5) or 0.5)

        consistency_score = float(np.clip(
            0.18 * referee_confidence
            + 0.16 * landing_confidence
            + 0.12 * direction_consistency
            + 0.16 * calibrated_confidence
            + 0.12 * signal_integrity
            + 0.12 * interpretation_stability
            + 0.14 * max(0.0, 1.0 - volatility)
            - 0.08 * len(contradictions),
            0.0,
            1.0,
        ))
        verdict_stability = float(np.clip(
            0.42 * calibrated_confidence
            + 0.26 * max(0.0, 1.0 - volatility)
            + 0.18 * interpretation_stability
            + 0.14 * direction_consistency,
            0.0,
            1.0,
        ))
        audit_level = self._audit_level(consistency_score, contradictions)

        return {
            "consistency_score": round(consistency_score, 3),
            "verdict_stability": round(verdict_stability, 3),
            "audit_level": audit_level,
            "contradictions": contradictions,
            "support_signals": support_signals,
            "recommended_action": self._recommended_action(audit_level, state),
            "audit_summary": self._audit_summary(audit_level, consistency_score, verdict_stability, contradictions),
        }

    def _collect_contradictions(
        self,
        state: Dict,
        tracker_diagnostics: Dict,
        rally_quality: Dict,
        confidence_report: Dict,
    ) -> List[str]:
        contradictions: List[str] = []
        auto_result = state.get("auto_result", "UNKNOWN")
        landing_margin = float(state.get("landing_margin", 0.0) or 0.0)
        landing_confidence = float(state.get("landing_confidence", 0.5) or 0.5)
        direction_consistency = float(state.get("direction_consistency", 0.5) or 0.5)
        signal_integrity = float(tracker_diagnostics.get("signal_integrity", 0.5) or 0.5)
        volatility = float(confidence_report.get("volatility", 0.0) or 0.0)
        interpretation_stability = float(rally_quality.get("interpretation_stability", 0.5) or 0.5)

        if auto_result != "UNKNOWN" and float(confidence_report.get("calibrated_confidence", 0.5) or 0.5) < 0.34:
            contradictions.append("A decisive verdict exists even though calibrated confidence remains low.")
        if abs(landing_margin) < 0.08 and landing_confidence > 0.72:
            contradictions.append("Landing margin is very small while landing confidence is unusually high.")
        if direction_consistency < 0.38 and auto_result != "UNKNOWN":
            contradictions.append("Last-hitter inference is weak for a resolved point outcome.")
        if signal_integrity < 0.35 and interpretation_stability > 0.68:
            contradictions.append("Tracker integrity is poor relative to the reported rally stability.")
        if volatility > 0.62 and auto_result in {"WIN", "LOSS"}:
            contradictions.append("Verdict volatility is high despite a binary win/loss call.")
        return contradictions

    def _collect_support_signals(
        self,
        state: Dict,
        tracker_diagnostics: Dict,
        motion_profile: Dict,
        confidence_report: Dict,
    ) -> List[str]:
        support_signals: List[str] = []
        if float(state.get("landing_confidence", 0.0) or 0.0) >= 0.62:
            support_signals.append("Landing geometry remained strong enough to support the call.")
        if float(state.get("direction_consistency", 0.0) or 0.0) >= 0.62:
            support_signals.append("Last-hitter direction inference was reasonably consistent.")
        if float(tracker_diagnostics.get("signal_integrity", 0.0) or 0.0) >= 0.64:
            support_signals.append("Tracker signal integrity stayed above the stable threshold.")
        if float(motion_profile.get("readiness_score", 0.0) or 0.0) >= 0.58:
            support_signals.append("Motion readiness supported the physical interpretation of the exchange.")
        if float(confidence_report.get("calibrated_confidence", 0.0) or 0.0) >= 0.66:
            support_signals.append("Cross-module confidence stayed high after calibration.")
        return support_signals

    def _audit_level(self, consistency_score: float, contradictions: List[str]) -> str:
        if consistency_score < 0.42 or len(contradictions) >= 3:
            return "escalate"
        if consistency_score < 0.68 or contradictions:
            return "watch"
        return "clean"

    def _recommended_action(self, audit_level: str, state: Dict) -> str:
        event_name = state.get("event", "rally")
        if audit_level == "escalate":
            return f"Treat the {event_name.lower()} verdict as provisional and favor conservative feedback wording."
        if audit_level == "watch":
            return f"Keep the {event_name.lower()} verdict, but surface a caution note to the player."
        return f"The {event_name.lower()} verdict is stable enough to use as a training signal."

    def _audit_summary(self, audit_level: str, consistency_score: float, verdict_stability: float, contradictions: List[str]) -> str:
        contradiction_note = "no major contradictions detected" if not contradictions else f"{len(contradictions)} contradiction(s) flagged"
        return (
            f"Referee audit level is {audit_level} with consistency {consistency_score:.2f} and verdict stability {verdict_stability:.2f}; "
            f"{contradiction_note}."
        )
