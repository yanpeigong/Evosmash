from __future__ import annotations

from collections import Counter, deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TelemetryService:
    def __init__(self, max_request_logs: int = 120, max_analysis_events: int = 80):
        self.max_request_logs = max_request_logs
        self.max_analysis_events = max_analysis_events
        self.request_logs: Deque[Dict[str, Any]] = deque(maxlen=max_request_logs)
        self.analysis_events: Deque[Dict[str, Any]] = deque(maxlen=max_analysis_events)
        self.feedback_events: Deque[Dict[str, Any]] = deque(maxlen=40)

    def record_request_started(self, request_id: str, method: str, path: str, client: str) -> None:
        self.request_logs.append(
            {
                "timestamp": _utc_now(),
                "stage": "started",
                "request_id": request_id,
                "method": method,
                "path": path,
                "client": client,
            }
        )

    def record_request_completed(self, request_id: str, method: str, path: str, status_code: int, duration_ms: float) -> None:
        self.request_logs.append(
            {
                "timestamp": _utc_now(),
                "stage": "completed",
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": round(float(duration_ms), 2),
            }
        )

    def record_request_failed(self, request_id: str, method: str, path: str, duration_ms: float) -> None:
        self.request_logs.append(
            {
                "timestamp": _utc_now(),
                "stage": "failed",
                "request_id": request_id,
                "method": method,
                "path": path,
                "duration_ms": round(float(duration_ms), 2),
            }
        )

    def record_analysis_request(self, request_id: str, endpoint: str, match_type: str, filename: str, size_bytes: int) -> None:
        self.analysis_events.append(
            {
                "timestamp": _utc_now(),
                "stage": "requested",
                "request_id": request_id,
                "endpoint": endpoint,
                "match_type": match_type,
                "filename": filename,
                "size_bytes": int(size_bytes),
            }
        )

    def record_analysis_response(self, request_id: str, endpoint: str, payload: Dict[str, Any]) -> None:
        event = {
            "timestamp": _utc_now(),
            "stage": "completed",
            "request_id": request_id,
            "endpoint": endpoint,
        }
        if endpoint == "analyze_rally":
            diagnostics = payload.get("diagnostics", {}) or {}
            event.update(
                {
                    "auto_result": payload.get("auto_result", "UNKNOWN"),
                    "analysis_quality": diagnostics.get("analysis_quality", "unknown"),
                    "warning_count": len(diagnostics.get("warnings", []) or []),
                    "tactic_count": len(payload.get("tactics", []) or []),
                }
            )
        else:
            summary = payload.get("match_summary", {}) or {}
            metrics = summary.get("metrics", {}) or {}
            event.update(
                {
                    "status": payload.get("status", "unknown"),
                    "valid_rallies_analyzed": summary.get("valid_rallies_analyzed", 0),
                    "total_rallies_found": summary.get("total_rallies_found", 0),
                    "peak_speed_kmh": metrics.get("peak_speed_kmh", 0.0),
                }
            )
        self.analysis_events.append(event)

    def record_feedback(self, request_id: str, tactic_id: str, result: str, reward: float) -> None:
        self.feedback_events.append(
            {
                "timestamp": _utc_now(),
                "request_id": request_id,
                "tactic_id": tactic_id,
                "result": result,
                "reward": reward,
            }
        )

    def summary(self) -> Dict[str, Any]:
        request_stage_distribution = Counter(item.get("stage", "unknown") for item in self.request_logs)
        endpoint_distribution = Counter(item.get("endpoint", "unknown") for item in self.analysis_events)
        result_distribution = Counter(item.get("auto_result", item.get("status", "unknown")) for item in self.analysis_events)
        durations = [float(item.get("duration_ms", 0.0) or 0.0) for item in self.request_logs if item.get("stage") == "completed"]
        average_duration_ms = round(sum(durations) / len(durations), 2) if durations else 0.0

        return {
            "request_log_capacity": self.max_request_logs,
            "analysis_event_capacity": self.max_analysis_events,
            "request_events_stored": len(self.request_logs),
            "analysis_events_stored": len(self.analysis_events),
            "feedback_events_stored": len(self.feedback_events),
            "request_stage_distribution": dict(request_stage_distribution),
            "analysis_endpoint_distribution": dict(endpoint_distribution),
            "analysis_result_distribution": dict(result_distribution),
            "average_completed_request_ms": average_duration_ms,
            "latest_request_id": self.request_logs[-1]["request_id"] if self.request_logs else None,
        }

    def recent_requests(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(self.request_logs)[-max(1, min(limit, self.max_request_logs)):]

    def recent_analysis_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(self.analysis_events)[-max(1, min(limit, self.max_analysis_events)):]

    def recent_feedback_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        return list(self.feedback_events)[-max(1, min(limit, len(self.feedback_events) or 1)):]

    def export_snapshot(self) -> Dict[str, Any]:
        return {
            "summary": self.summary(),
            "recent_requests": self.recent_requests(),
            "recent_analysis_events": self.recent_analysis_events(),
            "recent_feedback_events": self.recent_feedback_events(),
        }
