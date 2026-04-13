from __future__ import annotations

from collections import Counter
from typing import Dict, List


class TrainingPrescriptor:
    def build_rally_plan(self, state: Dict, tactics: List[Dict], diagnostics: Dict) -> Dict:
        top_tactic = tactics[0] if tactics else {}
        confidence_report = diagnostics.get("confidence_report", {}) or {}
        referee_audit = diagnostics.get("referee_audit", {}) or {}
        pressure_index = float(state.get("pressure_index", 0.5) or 0.5)
        confidence = float(confidence_report.get("calibrated_confidence", 0.5) or 0.5)
        risk_note = top_tactic.get("risk_note", "Stay organized before committing.")

        theme = self._theme(state, top_tactic, referee_audit)
        micro_goal = self._micro_goal(state, top_tactic, pressure_index)
        guardrail = referee_audit.get("recommended_action") or risk_note
        blocks = [
            self._block("Shadow Rehearsal", 8, "low", f"Pattern the entry into {theme.lower()} before shuttle contact."),
            self._block("Constraint Feed", 12, "medium", micro_goal),
            self._block("Pressure Finish", 10, "high" if pressure_index >= 0.62 else "medium", risk_note),
        ]

        return {
            "theme": theme,
            "priority": self._priority(confidence, pressure_index, referee_audit.get("audit_level", "watch")),
            "micro_goal": micro_goal,
            "guardrail": guardrail,
            "blocks": blocks,
        }

    def build_match_plan(self, intelligence: Dict, timeline: List[Dict]) -> Dict:
        attack_phases = [
            (item.get("physics", {}) or {}).get("attack_phase", "neutral")
            for item in timeline
            if item.get("physics")
        ]
        top_phases = Counter(attack_phases).most_common(2)
        recommended_focus = intelligence.get("recommended_focus", []) or []
        blocks = []
        for index, focus in enumerate(recommended_focus[:3], start=1):
            blocks.append(
                {
                    "label": f"Match Block {index}",
                    "goal": focus.replace("-", " "),
                    "duration_min": 14 if index == 1 else 10,
                }
            )

        return {
            "match_theme": intelligence.get("tactical_identity", "Adaptive"),
            "phase_distribution": [{"phase": phase, "count": count} for phase, count in top_phases],
            "focus_queue": recommended_focus[:3],
            "blocks": blocks,
        }

    def _theme(self, state: Dict, top_tactic: Dict, referee_audit: Dict) -> str:
        attack_phase = state.get("attack_phase", "neutral").replace("_", " ").title()
        tactic_name = top_tactic.get("name") or state.get("event", "Rally")
        audit_level = referee_audit.get("audit_level", "watch")
        if audit_level == "escalate":
            return f"Stabilize {attack_phase} Decision Quality"
        return f"{attack_phase} Execution Around {tactic_name}"

    def _micro_goal(self, state: Dict, top_tactic: Dict, pressure_index: float) -> str:
        recommended_action = top_tactic.get("recommended_action") or "Recover with a balanced base before the next shot."
        if pressure_index >= 0.65:
            return f"Preserve shape first, then apply: {recommended_action}"
        return f"Repeat the first clean cue and finish with: {recommended_action}"

    def _priority(self, confidence: float, pressure_index: float, audit_level: str) -> str:
        if audit_level == "escalate" or confidence < 0.42:
            return "stability-first"
        if pressure_index >= 0.66:
            return "pressure-management"
        return "pattern-reinforcement"

    def _block(self, label: str, duration_min: int, intensity: str, goal: str) -> Dict:
        return {
            "label": label,
            "duration_min": duration_min,
            "intensity": intensity,
            "goal": goal,
        }
