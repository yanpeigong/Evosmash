from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List


class InsightTimelineBuilder:
    def build(self, timeline: Iterable[Dict[str, Any]], match_type: str = "singles") -> Dict[str, Any]:
        timeline = list(timeline or [])
        return {
            "match_type": match_type,
            "headline": self._headline(timeline),
            "chapters": self._chapters(timeline),
            "turning_points": self._turning_points(timeline),
            "momentum_windows": self._momentum_windows(timeline),
            "risk_windows": self._risk_windows(timeline),
            "focus_journey": self._focus_journey(timeline),
            "confidence_curve": self._confidence_curve(timeline),
            "pressure_curve": self._pressure_curve(timeline),
            "tempo_profile": self._tempo_profile(timeline),
            "identity_summary": self._identity_summary(timeline),
        }

    def _headline(self, timeline: List[Dict[str, Any]]) -> str:
        if not timeline:
            return "No timeline data is available yet."
        result_distribution = Counter(item.get("auto_result", "UNKNOWN") for item in timeline)
        if result_distribution.get("WIN", 0) > result_distribution.get("LOSS", 0):
            return "The timeline trends toward successful pressure conversion."
        if result_distribution.get("LOSS", 0) > result_distribution.get("WIN", 0):
            return "The timeline trends toward reactive play under load."
        return "The timeline shows a balanced tactical exchange overall."

    def _chapters(self, timeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        chapters = []
        if not timeline:
            return chapters

        early = timeline[: max(1, len(timeline) // 3)]
        middle = timeline[max(1, len(timeline) // 3): max(2, 2 * len(timeline) // 3)]
        late = timeline[max(2, 2 * len(timeline) // 3):]

        chapter_map = [
            ("Opening", early),
            ("Middle Phase", middle),
            ("Closing Phase", late),
        ]
        for label, items in chapter_map:
            if not items:
                continue
            chapters.append(
                {
                    "label": label,
                    "summary": self._chapter_summary(items),
                    "signals": self._chapter_signals(items),
                    "recommended_focus": self._chapter_focus(items),
                }
            )
        return chapters

    def _chapter_summary(self, items: List[Dict[str, Any]]) -> str:
        results = Counter(item.get("auto_result", "UNKNOWN") for item in items)
        event_distribution = Counter(
            ((item.get("physics", {}) or {}).get("event", "Unknown"))
            for item in items
        )
        top_event = event_distribution.most_common(1)[0][0] if event_distribution else "Unknown"
        if results.get("WIN", 0) > results.get("LOSS", 0):
            return f"This chapter leaned positive and was shaped mostly by {top_event} patterns."
        if results.get("LOSS", 0) > results.get("WIN", 0):
            return f"This chapter carried more losses and repeatedly returned to {top_event} situations."
        return f"This chapter stayed balanced, with {top_event} appearing most often."

    def _chapter_signals(self, items: List[Dict[str, Any]]) -> List[str]:
        speeds = [float((item.get("physics", {}) or {}).get("max_speed_kmh", 0.0) or 0.0) for item in items]
        pressures = [float((item.get("physics", {}) or {}).get("pressure_index", 0.0) or 0.0) for item in items]
        focus_distribution = Counter(
            ((item.get("advice", {}) or {}).get("focus", "Recovery"))
            for item in items
        )

        def _avg(values: List[float]) -> float:
            return round(sum(values) / len(values), 2) if values else 0.0

        top_focus = focus_distribution.most_common(1)[0][0] if focus_distribution else "Recovery"
        return [
            f"Average max speed: {_avg(speeds)} km/h",
            f"Average pressure: {_avg(pressures)}",
            f"Most common focus: {top_focus}",
        ]

    def _chapter_focus(self, items: List[Dict[str, Any]]) -> str:
        focus_distribution = Counter(
            ((item.get("advice", {}) or {}).get("focus", "Recovery"))
            for item in items
        )
        focus = focus_distribution.most_common(1)[0][0] if focus_distribution else "Recovery"
        return f"Keep reinforcing {focus.lower()} before adding more tactical complexity."

    def _turning_points(self, timeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        turning_points = []
        previous_result = None
        for item in timeline:
            current_result = item.get("auto_result", "UNKNOWN")
            if previous_result is not None and current_result != previous_result:
                physics = item.get("physics", {}) or {}
                summary = item.get("summary", {}) or {}
                turning_points.append(
                    {
                        "rally_index": item.get("rally_index"),
                        "from": previous_result,
                        "to": current_result,
                        "event": physics.get("event", "Unknown"),
                        "headline": summary.get("headline", ""),
                    }
                )
            previous_result = current_result
        return turning_points

    def _momentum_windows(self, timeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        windows = []
        if not timeline:
            return windows

        window_size = 3
        for start in range(0, len(timeline), window_size):
            chunk = timeline[start:start + window_size]
            results = Counter(item.get("auto_result", "UNKNOWN") for item in chunk)
            label = "neutral"
            if results.get("WIN", 0) > results.get("LOSS", 0):
                label = "surging"
            elif results.get("LOSS", 0) > results.get("WIN", 0):
                label = "under-pressure"
            windows.append(
                {
                    "start_rally": chunk[0].get("rally_index"),
                    "end_rally": chunk[-1].get("rally_index"),
                    "label": label,
                    "result_distribution": dict(results),
                }
            )
        return windows

    def _risk_windows(self, timeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        windows = []
        for item in timeline:
            physics = item.get("physics", {}) or {}
            diagnostics = item.get("diagnostics", {}) or {}
            confidence = (((diagnostics.get("confidence_report", {}) or {}).get("calibrated_confidence", 0.0) or 0.0)
            pressure = float(physics.get("pressure_index", 0.0) or 0.0)
            quality = diagnostics.get("analysis_quality", "unknown")
            if pressure >= 0.65 or confidence <= 0.45 or quality in {"limited", "degraded", "low"}:
                windows.append(
                    {
                        "rally_index": item.get("rally_index"),
                        "pressure_index": pressure,
                        "confidence": confidence,
                        "analysis_quality": quality,
                        "note": self._risk_note(pressure, confidence, quality),
                    }
                )
        return windows

    def _risk_note(self, pressure: float, confidence: float, quality: str) -> str:
        if quality in {"limited", "degraded", "low"}:
            return "The analysis signal was weaker here, so tactical conclusions should be treated carefully."
        if pressure >= 0.7 and confidence <= 0.5:
            return "This window combined elevated pressure with weaker confidence, making it a strong coaching review point."
        if pressure >= 0.7:
            return "Pressure was elevated here, so recovery structure likely mattered more than tactical ambition."
        return "Confidence dipped enough here to justify a closer replay review."

    def _focus_journey(self, timeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        journey = []
        for item in timeline:
            advice = item.get("advice", {}) or {}
            journey.append(
                {
                    "rally_index": item.get("rally_index"),
                    "focus": advice.get("focus", "Recovery"),
                    "headline": advice.get("headline", ""),
                    "next_step": advice.get("next_step", ""),
                }
            )
        return journey

    def _confidence_curve(self, timeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        curve = []
        for item in timeline:
            diagnostics = item.get("diagnostics", {}) or {}
            confidence_report = diagnostics.get("confidence_report", {}) or {}
            curve.append(
                {
                    "rally_index": item.get("rally_index"),
                    "confidence": round(float(confidence_report.get("calibrated_confidence", 0.0) or 0.0), 3),
                    "label": self._confidence_label(float(confidence_report.get("calibrated_confidence", 0.0) or 0.0)),
                }
            )
        return curve

    def _pressure_curve(self, timeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        curve = []
        for item in timeline:
            physics = item.get("physics", {}) or {}
            pressure = float(physics.get("pressure_index", 0.0) or 0.0)
            curve.append(
                {
                    "rally_index": item.get("rally_index"),
                    "pressure_index": round(pressure, 3),
                    "label": self._pressure_label(pressure),
                }
            )
        return curve

    def _tempo_profile(self, timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        distribution = Counter(
            ((item.get("physics", {}) or {}).get("tempo_profile", "medium"))
            for item in timeline
        )
        speed_values = [float((item.get("physics", {}) or {}).get("max_speed_kmh", 0.0) or 0.0) for item in timeline]
        return {
            "tempo_distribution": dict(distribution),
            "speed_band": self._speed_band(speed_values),
            "average_speed_kmh": round(sum(speed_values) / len(speed_values), 3) if speed_values else 0.0,
        }

    def _identity_summary(self, timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        event_distribution = Counter(
            ((item.get("physics", {}) or {}).get("event", "Unknown"))
            for item in timeline
        )
        focus_distribution = Counter(
            ((item.get("advice", {}) or {}).get("focus", "Recovery"))
            for item in timeline
        )
        result_distribution = Counter(item.get("auto_result", "UNKNOWN") for item in timeline)
        dominant_event = event_distribution.most_common(1)[0][0] if event_distribution else "Unknown"
        dominant_focus = focus_distribution.most_common(1)[0][0] if focus_distribution else "Recovery"
        momentum = "neutral"
        if result_distribution.get("WIN", 0) > result_distribution.get("LOSS", 0):
            momentum = "surging"
        elif result_distribution.get("LOSS", 0) > result_distribution.get("WIN", 0):
            momentum = "under-pressure"
        return {
            "dominant_event": dominant_event,
            "dominant_focus": dominant_focus,
            "momentum": momentum,
            "summary": (
                f"The timeline is anchored by {dominant_event} patterns with a recurring emphasis on "
                f"{dominant_focus.lower()}, leaving the overall momentum state at {momentum}."
            ),
        }

    def _confidence_label(self, confidence: float) -> str:
        if confidence >= 0.75:
            return "high"
        if confidence <= 0.45:
            return "low"
        return "medium"

    def _pressure_label(self, pressure: float) -> str:
        if pressure >= 0.7:
            return "high"
        if pressure <= 0.35:
            return "low"
        return "medium"

    def _speed_band(self, speed_values: List[float]) -> str:
        if not speed_values:
            return "unknown"
        average = sum(speed_values) / len(speed_values)
        if average >= 140:
            return "fast"
        if average >= 85:
            return "medium"
        return "controlled"
