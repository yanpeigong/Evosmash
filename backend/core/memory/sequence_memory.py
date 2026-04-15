from __future__ import annotations

from collections import Counter
from typing import Dict, List

import numpy as np


class SequenceMemory:
    def build_context(self, timeline: List[Dict], match_type: str = "singles", window: int = 4) -> Dict:
        if not timeline:
            return self._empty_context(match_type, window)

        recent_items = timeline[-window:]
        recent_events = [item.get("physics", {}).get("event", "Unknown") for item in recent_items]
        recent_results = [item.get("auto_result", "UNKNOWN") for item in recent_items]
        recent_pressures = [float(item.get("physics", {}).get("pressure_index", 0.0) or 0.0) for item in recent_items]
        recent_phases = [item.get("physics", {}).get("attack_phase", "neutral") for item in recent_items]
        recent_tactics = [self._top_tactic_snapshot(item) for item in recent_items]
        tactic_transitions = self._transition_profile(recent_tactics)
        streak_context = self._streak_context(recent_results)
        pressure_swing = self._pressure_swing(recent_pressures)
        adaptation_signals = self._adaptation_signals(recent_events, recent_tactics, recent_pressures, recent_phases)
        player_adjustment_signals = self._player_adjustments(recent_items)
        event_distribution = dict(Counter(recent_events))
        tactic_distribution = dict(Counter(snapshot["name"] for snapshot in recent_tactics if snapshot.get("name")))
        style_distribution = dict(Counter(snapshot["style_family"] for snapshot in recent_tactics if snapshot.get("style_family")))
        sequence_tags = self._sequence_tags(streak_context, pressure_swing, adaptation_signals)
        preferred_style_family = max(style_distribution, key=style_distribution.get) if style_distribution else "balanced"
        continuity_anchor = recent_tactics[-1] if recent_tactics else {}
        adaptation_score = self._adaptation_score(recent_events, recent_tactics, recent_pressures)

        return {
            "match_type": match_type,
            "window_size": len(recent_items),
            "recent_events": recent_events,
            "recent_results": recent_results,
            "recent_pressures": [round(value, 3) for value in recent_pressures],
            "recent_phases": recent_phases,
            "recent_tactics": recent_tactics,
            "event_distribution": event_distribution,
            "tactic_distribution": tactic_distribution,
            "style_distribution": style_distribution,
            "tactic_transitions": tactic_transitions,
            "streak_context": streak_context,
            "pressure_swing": pressure_swing,
            "adaptation_signals": adaptation_signals,
            "player_adjustment_signals": player_adjustment_signals,
            "sequence_tags": sequence_tags,
            "preferred_style_family": preferred_style_family,
            "continuity_anchor": continuity_anchor,
            "adaptation_score": round(adaptation_score, 3),
            "memory_summary": self._memory_summary(streak_context, pressure_swing, adaptation_signals, continuity_anchor),
            "retrieval_context": {
                "recent_tactics": [snapshot.get("name", "Unknown") for snapshot in recent_tactics],
                "recent_events": recent_events,
                "streak_state": streak_context.get("state", "neutral"),
                "preferred_style_family": preferred_style_family,
                "pressure_script": pressure_swing.get("label", "steady"),
                "last_tactic": continuity_anchor.get("name", "Unknown"),
                "adaptation_score": round(adaptation_score, 3),
            },
        }

    def _empty_context(self, match_type: str, window: int) -> Dict:
        return {
            "match_type": match_type,
            "window_size": 0,
            "recent_events": [],
            "recent_results": [],
            "recent_pressures": [],
            "recent_phases": [],
            "recent_tactics": [],
            "event_distribution": {},
            "tactic_distribution": {},
            "style_distribution": {},
            "tactic_transitions": [],
            "streak_context": {"state": "neutral", "length": 0, "last_result": "UNKNOWN"},
            "pressure_swing": {"label": "steady", "delta": 0.0, "mean_pressure": 0.0},
            "adaptation_signals": [],
            "player_adjustment_signals": [],
            "sequence_tags": ["cold-start"],
            "preferred_style_family": "balanced",
            "continuity_anchor": {},
            "adaptation_score": 0.0,
            "memory_summary": "No previous rallies are available, so this is a cold-start tactical read.",
            "retrieval_context": {
                "recent_tactics": [],
                "recent_events": [],
                "streak_state": "neutral",
                "preferred_style_family": "balanced",
                "pressure_script": "steady",
                "last_tactic": "Unknown",
                "adaptation_score": 0.0,
            },
        }

    def _top_tactic_snapshot(self, item: Dict) -> Dict:
        tactic = (item.get("tactics") or [{}])[0] if item.get("tactics") else {}
        metadata = tactic.get("metadata", {}) or {}
        return {
            "rally_index": item.get("rally_index"),
            "name": tactic.get("name", "Unknown"),
            "tactic_id": metadata.get("tactic_id") or metadata.get("id") or "unknown",
            "style_family": metadata.get("style_family", "balanced"),
            "phase_preference": metadata.get("phase_preference", "neutral"),
            "risk_level": metadata.get("risk_level", "medium"),
            "score": float(tactic.get("rerank_score", tactic.get("score", 0.0)) or 0.0),
        }

    def _transition_profile(self, recent_tactics: List[Dict]) -> List[Dict]:
        transitions = []
        for previous, current in zip(recent_tactics, recent_tactics[1:]):
            transitions.append(
                {
                    "from": previous.get("name", "Unknown"),
                    "to": current.get("name", "Unknown"),
                    "style_shift": f"{previous.get('style_family', 'balanced')} -> {current.get('style_family', 'balanced')}",
                }
            )
        return transitions[-3:]

    def _streak_context(self, recent_results: List[str]) -> Dict:
        if not recent_results:
            return {"state": "neutral", "length": 0, "last_result": "UNKNOWN"}
        last_result = recent_results[-1]
        length = 0
        for result in reversed(recent_results):
            if result == last_result:
                length += 1
            else:
                break
        state = "surging" if last_result == "WIN" else ("under-pressure" if last_result == "LOSS" else "neutral")
        return {"state": state, "length": length, "last_result": last_result}

    def _pressure_swing(self, recent_pressures: List[float]) -> Dict:
        if not recent_pressures:
            return {"label": "steady", "delta": 0.0, "mean_pressure": 0.0}
        mean_pressure = float(np.mean(recent_pressures))
        delta = float(recent_pressures[-1] - recent_pressures[0]) if len(recent_pressures) > 1 else 0.0
        volatility = float(np.std(recent_pressures)) if len(recent_pressures) > 1 else 0.0
        if delta >= 0.14:
            label = "rising-pressure"
        elif delta <= -0.14:
            label = "releasing-pressure"
        elif volatility >= 0.12:
            label = "volatile-pressure"
        else:
            label = "steady-pressure"
        return {"label": label, "delta": round(delta, 3), "mean_pressure": round(mean_pressure, 3), "volatility": round(volatility, 3)}

    def _adaptation_signals(self, recent_events: List[str], recent_tactics: List[Dict], recent_pressures: List[float], recent_phases: List[str]) -> List[str]:
        signals: List[str] = []
        event_counter = Counter(recent_events)
        tactic_counter = Counter(snapshot.get("name", "Unknown") for snapshot in recent_tactics)
        phase_counter = Counter(recent_phases)
        if event_counter:
            dominant_event, event_count = event_counter.most_common(1)[0]
            if event_count >= 2:
                signals.append(f"The recent sequence keeps returning to {dominant_event.lower()} patterns.")
        if tactic_counter:
            dominant_tactic, tactic_count = tactic_counter.most_common(1)[0]
            if tactic_count >= 2:
                signals.append(f"{dominant_tactic} has been revisited repeatedly as the preferred answer.")
        if recent_pressures and recent_pressures[-1] >= 0.68:
            signals.append("Recent rallies are finishing under elevated pressure, so the tactical window is narrowing.")
        if phase_counter.get("under_pressure", 0) >= 2:
            signals.append("The match flow is spending too much time in under-pressure phases.")
        return signals[:3]

    def _player_adjustments(self, recent_items: List[Dict]) -> List[str]:
        adjustments: List[str] = []
        if len(recent_items) < 2:
            return adjustments
        latest = recent_items[-1]
        previous = recent_items[-2]
        latest_phase = latest.get("physics", {}).get("attack_phase", "neutral")
        previous_phase = previous.get("physics", {}).get("attack_phase", "neutral")
        latest_tactic = (latest.get("tactics") or [{}])[0].get("name", "Unknown") if latest.get("tactics") else "Unknown"
        previous_tactic = (previous.get("tactics") or [{}])[0].get("name", "Unknown") if previous.get("tactics") else "Unknown"
        if latest_phase != previous_phase:
            adjustments.append(f"Attack phase shifted from {previous_phase.replace('_', ' ')} to {latest_phase.replace('_', ' ')}.")
        if latest_tactic != previous_tactic:
            adjustments.append(f"Tactical preference changed from {previous_tactic} to {latest_tactic}.")
        latest_pressure = float(latest.get("physics", {}).get("pressure_index", 0.0) or 0.0)
        previous_pressure = float(previous.get("physics", {}).get("pressure_index", 0.0) or 0.0)
        if latest_pressure + 0.12 < previous_pressure:
            adjustments.append("Pressure load dropped after the latest tactical adjustment.")
        return adjustments[:3]

    def _sequence_tags(self, streak_context: Dict, pressure_swing: Dict, adaptation_signals: List[str]) -> List[str]:
        tags = [pressure_swing.get("label", "steady-pressure")]
        if streak_context.get("state") != "neutral":
            tags.append(f"{streak_context.get('state')}-streak")
        if adaptation_signals:
            tags.append("adaptation-live")
        return tags

    def _adaptation_score(self, recent_events: List[str], recent_tactics: List[Dict], recent_pressures: List[float]) -> float:
        if not recent_events:
            return 0.0
        event_variety = len(set(recent_events)) / max(len(recent_events), 1)
        tactic_variety = len({snapshot.get("name", "Unknown") for snapshot in recent_tactics}) / max(len(recent_tactics), 1)
        pressure_volatility = float(np.std(recent_pressures)) if len(recent_pressures) > 1 else 0.0
        return float(np.clip(0.36 * event_variety + 0.42 * tactic_variety + 0.22 * min(pressure_volatility * 4.0, 1.0), 0.0, 1.0))

    def _memory_summary(self, streak_context: Dict, pressure_swing: Dict, adaptation_signals: List[str], continuity_anchor: Dict) -> str:
        streak_state = streak_context.get("state", "neutral").replace("-", " ")
        anchor_name = continuity_anchor.get("name", "Unknown")
        swing = pressure_swing.get("label", "steady-pressure").replace("-", " ")
        if adaptation_signals:
            return f"Sequence memory sees a {streak_state} flow with {swing} and {anchor_name} acting as the latest anchor. {adaptation_signals[0]}"
        return f"Sequence memory sees a {streak_state} flow with {swing}, anchored most recently by {anchor_name}."
