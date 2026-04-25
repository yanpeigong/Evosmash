import io
import os
import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


class FakeAnalysisService:
    def analyze_rally(self, filepath, match_type):
        return {
            "physics": {
                "event": "Drive Exchange",
                "max_speed_kmh": 82.4,
                "description": "Stub rally analysis.",
                "coordinates": [],
                "auto_result": "WIN",
                "match_type": match_type,
            },
            "advice": {
                "text": "Recover fast and prepare early.",
                "headline": "Stay sharp",
                "focus": "Recovery",
                "next_step": "Split step before contact.",
                "confidence_label": "high",
                "source": "stub",
            },
            "tactics": [
                {
                    "name": "Front Court Hold",
                    "content": "Recover early and hold the forecourt.",
                    "score": 0.91,
                    "metadata": {"tactic_id": "tactic-1", "alpha": 4.0, "beta": 1.0},
                }
            ],
            "session_id": "tactic-1",
            "match_type": match_type,
            "auto_result": "WIN",
            "auto_reward": 9.0,
            "summary": {
                "headline": "Winning pattern detected",
                "verdict": "WIN",
                "confidence_label": "high",
                "key_takeaway": "Primary tactical direction: Front Court Hold.",
            },
            "diagnostics": {
                "warnings": [],
                "pipeline": {"tracking": "ok", "physics": "ok", "retrieval": "ok", "coach": "ok"},
                "motion_feedback": "Ready",
                "trajectory_points": 12,
                "analysis_quality": "high",
            },
            "report": {"headline": "Rally analyzed"},
        }

    def analyze_match(self, filepath, match_type):
        return {
            "status": "success",
            "match_summary": {
                "total_rallies_found": 3,
                "valid_rallies_analyzed": 2,
                "metrics": {
                    "result_distribution": {"WIN": 1, "LOSS": 1},
                    "average_rally_duration_sec": 4.2,
                    "average_max_speed_kmh": 88.4,
                    "peak_speed_kmh": 121.0,
                    "average_pressure_index": 0.44,
                    "average_confidence": 0.78,
                    "top_focuses": [{"focus": "Recovery", "count": 2}],
                    "top_tactics": [{"name": "Front Court Hold", "count": 2}],
                    "analysis_quality_distribution": {"high": 2},
                },
                "intelligence": {},
                "sequence_memory": {},
                "duel_summary": {},
                "replay_story": {},
                "report": {},
            },
            "timeline": [
                {
                    "rally_index": 1,
                    "duration_sec": 3.8,
                    "physics": {
                        "event": "Drive Exchange",
                        "max_speed_kmh": 82.4,
                        "description": "Stub rally analysis.",
                        "coordinates": [],
                        "auto_result": "WIN",
                        "match_type": match_type,
                    },
                    "advice": {
                        "text": "Recover fast and prepare early.",
                        "headline": "Stay sharp",
                        "focus": "Recovery",
                        "next_step": "Split step before contact.",
                        "confidence_label": "high",
                        "source": "stub",
                    },
                    "tactics": [
                        {
                            "name": "Front Court Hold",
                            "content": "Recover early and hold the forecourt.",
                            "score": 0.91,
                            "metadata": {"tactic_id": "tactic-1", "alpha": 4.0, "beta": 1.0},
                        }
                    ],
                    "auto_result": "WIN",
                    "auto_reward": 9.0,
                    "summary": {
                        "headline": "Winning pattern detected",
                        "verdict": "WIN",
                        "confidence_label": "high",
                        "key_takeaway": "Primary tactical direction: Front Court Hold.",
                    },
                    "diagnostics": {
                        "warnings": [],
                        "pipeline": {"tracking": "ok", "physics": "ok", "retrieval": "ok", "coach": "ok"},
                        "motion_feedback": "Ready",
                        "trajectory_points": 12,
                        "analysis_quality": "high",
                    },
                    "report": {"headline": "Rally analyzed"},
                }
            ],
            "warnings": [],
        }


class FakePhysics:
    def calculate_reward(self, result):
        return {"WIN": 10.0, "LOSS": -5.0}.get(result, 0.0)


class FakeRAG:
    def update_policy(self, tactic_id, reward, context=None):
        return {"status": "ok", "tactic_id": tactic_id, "reward": reward, "context": context or {}}


class FakeRuntime:
    def __init__(self, analysis_ready=True):
        self.analysis_service = FakeAnalysisService() if analysis_ready else None
        self.physics = FakePhysics()
        self.rag = FakeRAG()
        self._analysis_ready = analysis_ready

    def is_ready_for_analysis(self):
        return self.analysis_service is not None

    def overall_status(self):
        return "ok" if self.analysis_service is not None else "degraded"

    def build_status_payload(self):
        return {
            "status": self.overall_status(),
            "analysis_ready": self.is_ready_for_analysis(),
            "components": {
                "tracker": {"status": "ready", "critical": True},
                "physics": {"status": "ready", "critical": True},
            },
            "summary": {"ready": 2, "fallback": 0, "failed": 0},
        }


@pytest.fixture
def fake_runtime():
    return FakeRuntime()


@pytest.fixture
def client(fake_runtime):
    from main import create_app

    app = create_app(runtime_override=fake_runtime)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def unavailable_client():
    from main import create_app

    app = create_app(runtime_override=FakeRuntime(analysis_ready=False))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def video_upload():
    return {
        "file": ("demo.mp4", io.BytesIO(b"fake-video-content"), "video/mp4"),
    }
