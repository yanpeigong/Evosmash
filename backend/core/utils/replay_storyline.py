from __future__ import annotations

from typing import Dict, List

import numpy as np


class ReplayStorylineBuilder:
    def build(self, timeline: List[Dict], intelligence: Dict, sequence_context: Dict | None = None, duel_summary: Dict | None = None) -> Dict:
        sequence_context = sequence_context or {}
        duel_summary = duel_summary or {}
        if not timeline:
            return {
                "opening_phase": {},
                "turning_points": [],
                "adaptation_cycles": [],
                "critical_rallies": [],
                "closing_state": {},
                "storyline_cards": [],
                "timeline_digest": [],
                "replay_summary": "No replay storyline is available.",
            }

        opening_phase = self._opening_phase(timeline[: min(3, len(timeline))])
        turning_points = self._turning_points(timeline)
        adaptation_cycles = self._adaptation_cycles(timeline, sequence_context)
        critical_rallies = self._critical_rallies(timeline)
        closing_state = self._closing_state(timeline[-1], intelligence, duel_summary)
        timeline_digest = self._timeline_digest(timeline)
        storyline_cards = self._storyline_cards(opening_phase, turning_points, adaptation_cycles, closing_state)

        return {
            "opening_phase": opening_phase,
            "turning_points": turning_points,
            "adaptation_cycles": adaptation_cycles,
            "critical_rallies": critical_rallies,
            "closing_state": closing_state,
            "storyline_cards": storyline_cards,
            "timeline_digest": timeline_digest,
            "replay_summary": self._summary(opening_phase, turning_points, closing_state),
        }

    def _opening_phase(self, opening_items: List[Dict]) -> Dict:
        if not opening_items:
            return {}
        events = [item.get("physics", {}).get("event", "Unknown") for item in opening_items]
        tactics = [
            (item.get("tactics") or [{}])[0].get("name", "Unknown")
            for item in opening_items
            if item.get("tactics")
        ]
        avg_pressure = float(np.mean([float(item.get("physics", {}).get("pressure_index", 0.0) or 0.0) for item in opening_items]))
        return {
            "headline": "Opening phase",
            "events": events,
            "tactics": tactics,
            "average_pressure": round(avg_pressure, 3),
            "summary": f"The match opened around {' / '.join(events[:2]) if events else 'unknown patterns'} with average pressure {avg_pressure:.2f}.",
        }

    def _turning_points(self, timeline: List[Dict]) -> List[Dict]:
        turning_points = []
        if len(timeline) < 2:
            return turning_points
        pressures = [float(item.get("physics", {}).get("pressure_index", 0.0) or 0.0) for item in timeline]
        mean_pressure = float(np.mean(pressures)) if pressures else 0.0
        std_pressure = float(np.std(pressures)) if len(pressures) > 1 else 0.0
        threshold = mean_pressure + std_pressure

        for previous, current in zip(timeline, timeline[1:]):
            prev_result = previous.get("auto_result", "UNKNOWN")
            curr_result = current.get("auto_result", "UNKNOWN")
            prev_tactic = (previous.get("tactics") or [{}])[0].get("name", "Unknown") if previous.get("tactics") else "Unknown"
            curr_tactic = (current.get("tactics") or [{}])[0].get("name", "Unknown") if current.get("tactics") else "Unknown"
            current_pressure = float(current.get("physics", {}).get("pressure_index", 0.0) or 0.0)
            if curr_result != prev_result or current_pressure >= threshold or curr_tactic != prev_tactic:
                turning_points.append(
                    {
                        "rally_index": current.get("rally_index"),
                        "trigger": self._turning_trigger(prev_result, curr_result, prev_tactic, curr_tactic, current_pressure, threshold),
                        "summary": current.get("summary", {}).get("headline", "Rally shift"),
                    }
                )
        return turning_points[:4]

    def _adaptation_cycles(self, timeline: List[Dict], sequence_context: Dict) -> List[Dict]:
        transitions = sequence_context.get("tactic_transitions", []) or []
        cycles = []
        for transition in transitions[:3]:
            cycles.append(
                {
                    "from": transition.get("from", "Unknown"),
                    "to": transition.get("to", "Unknown"),
                    "style_shift": transition.get("style_shift", "balanced -> balanced"),
                    "summary": f"The sequence evolved from {transition.get('from', 'Unknown')} to {transition.get('to', 'Unknown')}."
                }
            )
        if not cycles and timeline:
            latest = timeline[-1]
            cycles.append(
                {
                    "from": "Opening read",
                    "to": (latest.get("tactics") or [{}])[0].get("name", "Unknown") if latest.get("tactics") else "Unknown",
                    "style_shift": "single-anchor",
                    "summary": "The available timeline is too short for a full adaptation cycle, so the latest rally acts as the current anchor.",
                }
            )
        return cycles

    def _critical_rallies(self, timeline: List[Dict]) -> List[Dict]:
        scored = []
        for item in timeline:
            pressure = float(item.get("physics", {}).get("pressure_index", 0.0) or 0.0)
            duel_risk = float(((item.get("diagnostics", {}) or {}).get("duel_projection", {}) or {}).get("duel_risk", 0.0) or 0.0)
            reward = abs(float(item.get("auto_reward", 0.0) or 0.0))
            score = 0.42 * pressure + 0.28 * duel_risk + 0.3 * min(reward / 10.0, 1.0)
            scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        critical = []
        for score, item in scored[:3]:
            critical.append(
                {
                    "rally_index": item.get("rally_index"),
                    "score": round(score, 3),
                    "headline": item.get("summary", {}).get("headline", "Critical rally"),
                    "takeaway": item.get("summary", {}).get("key_takeaway", ""),
                }
            )
        return critical

    def _closing_state(self, last_item: Dict, intelligence: Dict, duel_summary: Dict) -> Dict:
        last_tactic = (last_item.get("tactics") or [{}])[0].get("name", "Unknown") if last_item.get("tactics") else "Unknown"
        return {
            "last_rally_index": last_item.get("rally_index"),
            "verdict": last_item.get("auto_result", "UNKNOWN"),
            "tactic_anchor": last_tactic,
            "momentum_state": intelligence.get("momentum_state", "neutral"),
            "dominant_duel": duel_summary.get("dominant_duel", "unavailable"),
            "summary": f"The replay closes with {last_tactic} as the latest anchor and a {intelligence.get('momentum_state', 'neutral')} momentum state.",
        }

    def _timeline_digest(self, timeline: List[Dict]) -> List[Dict]:
        digest = []
        for item in timeline:
            tactic = (item.get("tactics") or [{}])[0].get("name", "Unknown") if item.get("tactics") else "Unknown"
            digest.append(
                {
                    "rally_index": item.get("rally_index"),
                    "event": item.get("physics", {}).get("event", "Unknown"),
                    "verdict": item.get("auto_result", "UNKNOWN"),
                    "top_tactic": tactic,
                    "pressure": round(float(item.get("physics", {}).get("pressure_index", 0.0) or 0.0), 3),
                }
            )
        return digest

    def _storyline_cards(self, opening_phase: Dict, turning_points: List[Dict], adaptation_cycles: List[Dict], closing_state: Dict) -> List[Dict]:
        cards = []
        if opening_phase:
            cards.append({"stage": "opening", "title": opening_phase.get("headline", "Opening"), "body": opening_phase.get("summary", "")})
        for turning_point in turning_points[:2]:
            cards.append({"stage": "turn", "title": f"Rally {turning_point.get('rally_index')}", "body": turning_point.get("trigger", "")})
        for cycle in adaptation_cycles[:2]:
            cards.append({"stage": "adapt", "title": cycle.get("to", "Adaptation"), "body": cycle.get("summary", "")})
        if closing_state:
            cards.append({"stage": "closing", "title": "Closing state", "body": closing_state.get("summary", "")})
        return cards

    def _summary(self, opening_phase: Dict, turning_points: List[Dict], closing_state: Dict) -> str:
        opening_text = opening_phase.get("summary", "The opening phase is unavailable.")
        turn_text = f"The main turning point arrived around rally {turning_points[0].get('rally_index', '?')}." if turning_points else "No major turning point was isolated from the current timeline."
        closing_text = closing_state.get("summary", "The closing state is unavailable.")
        return f"{opening_text} {turn_text} {closing_text}"

    def _turning_trigger(self, prev_result: str, curr_result: str, prev_tactic: str, curr_tactic: str, current_pressure: float, threshold: float) -> str:
        if curr_result != prev_result:
            return f"The result flipped from {prev_result} to {curr_result}, shifting match momentum."
        if curr_tactic != prev_tactic:
            return f"The tactical anchor shifted from {prev_tactic} to {curr_tactic}."
        if current_pressure >= threshold:
            return f"Pressure spiked to {current_pressure:.2f}, creating a high-leverage rally."
        return "The rally changed the flow without a single dominant trigger."
