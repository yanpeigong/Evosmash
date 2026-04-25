from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Callable, Dict, Optional

import numpy as np


class NullCourtDetector:
    def detect(self, frame):
        if frame is None or not hasattr(frame, "shape"):
            return np.array(
                [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
                dtype=np.float32,
            )

        height, width = frame.shape[:2]
        return np.array(
            [
                [width * 0.2, height * 0.3],
                [width * 0.8, height * 0.3],
                [width * 0.9, height * 0.9],
                [width * 0.1, height * 0.9],
            ],
            dtype=np.float32,
        )


class NullPoseAnalyzer:
    def infer(self, video_path):
        return []

    def evaluate_motion(self, pose_seq):
        return "Pose analysis unavailable."

    def evaluate_motion_profile(self, pose_seq):
        return {
            "feedback_text": "Pose analysis unavailable.",
            "quality_label": "unavailable",
            "readiness_score": 0.0,
        }


class NullRAGEngine:
    def retrieve(self, query_text, context=None, n_results=3):
        return []

    def update_policy(self, tactic_id, reward, context=None):
        return {
            "status": "skipped",
            "reason": "retrieval_engine_unavailable",
            "tactic_id": tactic_id,
            "reward": reward,
        }


class NullCoachAgent:
    def is_available(self) -> bool:
        return False

    def generate_structured_advice(self, state, tactics):
        top_tactic = tactics[0]["name"] if tactics else state.get("event", "the next pattern")
        return {
            "text": "Stay balanced, recover fast, and prepare early.",
            "headline": f"Play into {top_tactic}",
            "focus": state.get("attack_phase", "Shot selection").replace("_", " ").title(),
            "next_step": tactics[0].get("recommended_action", "Prepare for the next shot.") if tactics else "Prepare for the next shot.",
            "confidence_label": tactics[0].get("confidence_label", "medium") if tactics else "medium",
            "source": "runtime-fallback",
        }

    def generate_advice(self, state, tactics):
        return self.generate_structured_advice(state, tactics).get("text", "Stay balanced, recover fast, and prepare early.")


@dataclass
class BackendRuntime:
    tracker: Optional[Any]
    court_detector: Any
    pose_analyzer: Any
    physics: Optional[Any]
    rag: Any
    coach: Any
    analysis_service: Optional[Any]
    component_status: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def is_ready_for_analysis(self) -> bool:
        return self.analysis_service is not None

    def critical_failures(self) -> list[str]:
        return [
            name
            for name, payload in self.component_status.items()
            if payload.get("critical") and payload.get("status") == "failed"
        ]

    def readiness_score(self) -> float:
        if not self.component_status:
            return 0.0

        score = 0.0
        total_weight = 0.0
        for payload in self.component_status.values():
            status = payload.get("status", "unknown")
            critical = bool(payload.get("critical", False))
            weight = 1.7 if critical else 1.0
            total_weight += weight
            if status == "ready":
                score += weight
            elif status == "fallback":
                score += weight * 0.55
            elif status == "failed":
                score += 0.0
            else:
                score += weight * 0.2

        return round(score / total_weight, 3) if total_weight else 0.0

    def healthy_components(self) -> list[str]:
        return [
            name
            for name, payload in self.component_status.items()
            if payload.get("status") == "ready"
        ]

    def degraded_components(self) -> list[str]:
        return [
            name
            for name, payload in self.component_status.items()
            if payload.get("status") in {"fallback", "failed"}
        ]

    def component_matrix(self) -> list[Dict[str, Any]]:
        matrix = []
        for name, payload in self.component_status.items():
            status = payload.get("status", "unknown")
            critical = bool(payload.get("critical", False))
            readiness_score = 1.0 if status == "ready" else 0.55 if status == "fallback" else 0.0
            matrix.append(
                {
                    "name": name,
                    "status": status,
                    "critical": critical,
                    "class_name": payload.get("class_name"),
                    "readiness_score": round(readiness_score, 3),
                    "tags": [
                        "critical" if critical else "optional",
                        "operational" if status == "ready" else "degraded",
                    ],
                }
            )
        return matrix

    def overall_status(self) -> str:
        statuses = {item.get("status", "unknown") for item in self.component_status.values()}
        if self.analysis_service is None or "failed" in statuses:
            return "degraded"
        if "fallback" in statuses:
            return "degraded"
        return "ok"

    def build_status_payload(self) -> Dict[str, Any]:
        ready_components = sum(1 for item in self.component_status.values() if item.get("status") == "ready")
        fallback_components = sum(1 for item in self.component_status.values() if item.get("status") == "fallback")
        failed_components = sum(1 for item in self.component_status.values() if item.get("status") == "failed")
        readiness_score = self.readiness_score()
        healthy_components = self.healthy_components()
        degraded_components = self.degraded_components()
        return {
            "status": self.overall_status(),
            "analysis_ready": self.is_ready_for_analysis(),
            "components": {
                name: {
                    **payload,
                    "readiness_score": 1.0 if payload.get("status") == "ready" else 0.55 if payload.get("status") == "fallback" else 0.0,
                    "tags": [
                        "critical" if payload.get("critical") else "optional",
                        "operational" if payload.get("status") == "ready" else "degraded",
                    ],
                }
                for name, payload in self.component_status.items()
            },
            "summary": {
                "ready": ready_components,
                "fallback": fallback_components,
                "failed": failed_components,
                "readiness_score": readiness_score,
                "critical_failures": self.critical_failures(),
            },
            "insights": {
                "component_order": list(self.component_status.keys()),
                "healthy_components": healthy_components,
                "degraded_components": degraded_components,
                "critical_components": [
                    name for name, payload in self.component_status.items() if payload.get("critical")
                ],
                "component_matrix": self.component_matrix(),
            },
        }


def _load_component(
    statuses: Dict[str, Dict[str, Any]],
    name: str,
    factory: Callable[[], Any],
    fallback_factory: Optional[Callable[[], Any]] = None,
    critical: bool = False,
):
    try:
        instance = factory()
        statuses[name] = {
            "status": "ready",
            "class_name": instance.__class__.__name__,
            "detail": "",
            "critical": critical,
        }
        return instance
    except Exception as error:
        if fallback_factory is not None:
            fallback = fallback_factory()
            statuses[name] = {
                "status": "fallback",
                "class_name": fallback.__class__.__name__,
                "detail": str(error),
                "critical": critical,
            }
            return fallback

        statuses[name] = {
            "status": "failed",
            "class_name": None,
            "detail": str(error),
            "critical": critical,
        }
        return None


def _import_factory(module_path: str, class_name: str) -> Callable[[], Any]:
    def _factory():
        module = import_module(module_path)
        component_cls = getattr(module, class_name)
        return component_cls()

    return _factory


def bootstrap_runtime() -> BackendRuntime:
    statuses: Dict[str, Dict[str, Any]] = {}

    tracker = _load_component(statuses, "tracker", _import_factory("core.vision.tracker", "BallTracker"), critical=True)
    court_detector = _load_component(
        statuses,
        "court_detector",
        _import_factory("core.vision.court_detector", "CourtDetector"),
        fallback_factory=NullCourtDetector,
    )
    pose_analyzer = _load_component(
        statuses,
        "pose_analyzer",
        _import_factory("core.vision.pose", "PoseAnalyzer"),
        fallback_factory=NullPoseAnalyzer,
    )
    physics = _load_component(statuses, "physics", _import_factory("core.physics.engine", "PhysicsEngine"), critical=True)
    rag = _load_component(statuses, "rag", _import_factory("core.memory.rag_engine", "RAGEngine"), fallback_factory=NullRAGEngine)
    coach = _load_component(statuses, "coach", _import_factory("core.agent.llm", "CoachAgent"), fallback_factory=NullCoachAgent)

    analysis_service = None
    if tracker is not None and physics is not None:
        AnalysisService = getattr(import_module("services.analysis_service"), "AnalysisService")
        analysis_service = AnalysisService(
            tracker=tracker,
            court_detector=court_detector,
            pose_analyzer=pose_analyzer,
            physics=physics,
            rag=rag,
            coach=coach,
        )

    return BackendRuntime(
        tracker=tracker,
        court_detector=court_detector,
        pose_analyzer=pose_analyzer,
        physics=physics,
        rag=rag,
        coach=coach,
        analysis_service=analysis_service,
        component_status=statuses,
    )
