from __future__ import annotations

from typing import Any, Dict, List


def build_demo_rally_payload(match_type: str = "singles") -> Dict[str, Any]:
    tactics: List[Dict[str, Any]] = [
        {
            "name": "Front Court Hold",
            "content": "Recover early, hold the forecourt, and force a soft lift before accelerating.",
            "score": 0.912,
            "semantic_score": 0.81,
            "bayesian_score": 0.87,
            "context_score": 0.83,
            "expected_win_rate": 76.4,
            "confidence_label": "high",
            "recommended_action": "Recover early and threaten the net hold.",
            "reason": "This option fits the pressure profile and rewards early preparation.",
            "why_this_tactic": "The rally is already leaning into forecourt pressure, so a compact hold can preserve initiative.",
            "risk_note": "Only commit if your base is stable enough to cover the counter-lift.",
            "metadata": {
                "tactic_id": "demo-front-court-hold",
                "alpha": 8.0,
                "beta": 2.0,
                "style_family": "front-pressure",
                "risk_level": "medium",
            },
            "fit_breakdown": {
                "event_fit": 0.84,
                "phase_fit": 0.88,
                "tempo_fit": 0.81,
            },
        },
        {
            "name": "Deep Clear Reset",
            "content": "Lift deep crosscourt to reset spacing and buy recovery time.",
            "score": 0.724,
            "semantic_score": 0.72,
            "bayesian_score": 0.68,
            "context_score": 0.71,
            "expected_win_rate": 61.8,
            "confidence_label": "medium",
            "recommended_action": "Choose height and depth before adding pace.",
            "reason": "Useful when the rally needs structure more than immediate pressure.",
            "why_this_tactic": "A deep reset keeps the opponent from attacking the empty forecourt too early.",
            "risk_note": "Short depth turns this into a feeding ball, so prioritize length first.",
            "metadata": {
                "tactic_id": "demo-deep-clear-reset",
                "alpha": 6.0,
                "beta": 4.0,
                "style_family": "reset",
                "risk_level": "low",
            },
            "fit_breakdown": {
                "event_fit": 0.69,
                "phase_fit": 0.74,
                "tempo_fit": 0.7,
            },
        },
    ]

    return {
        "physics": {
            "event": "Pressure Rally",
            "max_speed_kmh": 144.2,
            "description": "Mode: Demo. Event: Pressure Rally. Max shuttle speed 144 km/h. Verdict: point won. Phase under_pressure, tempo fast, shot shape direct-pressure.",
            "coordinates": [],
            "auto_result": "WIN",
            "match_type": match_type,
            "trajectory_quality": 0.81,
            "referee_confidence": 0.77,
            "referee_reason": "Demo verdict generated for UI and API integration.",
            "landing_confidence": 0.72,
            "direction_consistency": 0.75,
            "landing_margin": 0.48,
            "court_context": "front_central",
            "last_hitter": "USER",
            "landing_point": [2.84, 3.2],
            "attack_phase": "under_pressure",
            "tempo_profile": "fast",
            "shot_shape": "direct-pressure",
            "pressure_index": 0.67,
            "trajectory_features": {
                "visibility_ratio": 0.81,
                "route_directness": 0.76,
                "sample_count": 18,
                "terminal_settle": 0.63,
            },
            "referee_trace": {"decision": "win", "tail_bias": -0.24},
            "rally_state": {
                "trajectory_quality": 0.81,
                "landing_confidence": 0.72,
                "direction_consistency": 0.75,
                "court_context": "front_central",
            },
        },
        "advice": {
            "text": "Stabilize your base first, then hold the forecourt with intent.",
            "headline": "Own the forecourt",
            "focus": "Recovery",
            "next_step": "Split early and show the hold before contact.",
            "confidence_label": "high",
            "source": "demo",
        },
        "tactics": tactics,
        "session_id": "demo-front-court-hold",
        "match_type": match_type,
        "auto_result": "WIN",
        "auto_reward": 9.63,
        "summary": {
            "headline": "Winning pattern detected",
            "verdict": "WIN",
            "confidence_label": "high",
            "key_takeaway": "Primary tactical direction: Front Court Hold. The rally profile rewards early recovery and controlled forecourt pressure.",
        },
        "diagnostics": {
            "warnings": [],
            "pipeline": {
                "court_detection": "ok",
                "tracking": "ok",
                "pose": "ok",
                "physics": "ok",
                "retrieval": "ok",
                "coach": "ok",
            },
            "motion_feedback": "Base stays active and recovery timing is compatible with a forecourt hold pattern.",
            "trajectory_points": 18,
            "analysis_quality": "high",
            "retrieval_summary": {
                "selected_tactic": "Front Court Hold",
                "score": 0.912,
                "expected_win_rate": 76.4,
                "style_family": "front-pressure",
            },
            "physics_profile": {
                "attack_phase": "under_pressure",
                "tempo_profile": "fast",
                "shot_shape": "direct-pressure",
                "pressure_index": 0.67,
            },
            "tracker_diagnostics": {
                "signal_integrity": 0.84,
                "repaired_points": 1,
                "spike_count": 0,
            },
            "motion_profile": {
                "quality_label": "assertive",
                "readiness_score": 0.79,
            },
            "rally_quality": {
                "overall_quality": 0.82,
                "tempo_score": 0.78,
                "pressure_score": 0.73,
            },
            "confidence_report": {
                "calibrated_confidence": 0.8,
                "stability_label": "stable",
            },
            "referee_audit": {
                "audit_level": "watch",
                "verdict_stability": 0.76,
            },
            "sequence_context": {
                "memory_summary": "Demo sequence favors front-pressure conversions after stable recovery.",
                "sequence_tags": ["demo", "front-pressure", "recovery-first"],
            },
            "duel_projection": {
                "duel_edge": "user",
                "projected_edge_score": 0.18,
            },
            "policy_update": {
                "status": "demo",
                "policy_update_reason": "This payload is intended for integration previews.",
            },
        },
        "report": {
            "headline": "Demo Rally Report",
            "coach_takeaway": "Use the forecourt hold only after the base is already organized.",
            "training_plan": {
                "theme": "Recovery Into Front Court Hold",
                "priority": "pattern-reinforcement",
                "blocks": [
                    {"label": "Shadow Rehearsal", "duration_min": 8, "intensity": "low"},
                    {"label": "Constraint Feed", "duration_min": 12, "intensity": "medium"},
                ],
            },
        },
    }


def build_demo_match_payload(match_type: str = "singles") -> Dict[str, Any]:
    rally_item = build_demo_rally_payload(match_type=match_type)
    timeline = []
    for index in range(1, 4):
        rally_copy = {
            "rally_index": index,
            "duration_sec": round(3.4 + index * 0.6, 2),
            "physics": {**rally_item["physics"], "max_speed_kmh": round(rally_item["physics"]["max_speed_kmh"] + index * 5.3, 1)},
            "advice": rally_item["advice"],
            "tactics": rally_item["tactics"],
            "auto_result": "WIN" if index != 2 else "LOSS",
            "auto_reward": 8.4 if index != 2 else -4.2,
            "summary": rally_item["summary"],
            "diagnostics": rally_item["diagnostics"],
            "report": rally_item["report"],
        }
        timeline.append(rally_copy)

    return {
        "status": "success",
        "match_summary": {
            "total_rallies_found": 3,
            "valid_rallies_analyzed": 3,
            "metrics": {
                "result_distribution": {"WIN": 2, "LOSS": 1},
                "average_rally_duration_sec": 4.6,
                "average_max_speed_kmh": 154.8,
                "peak_speed_kmh": 160.1,
                "average_pressure_index": 0.64,
                "average_confidence": 0.79,
                "top_focuses": [{"focus": "Recovery", "count": 3}],
                "top_tactics": [{"name": "Front Court Hold", "count": 2}, {"name": "Deep Clear Reset", "count": 1}],
                "analysis_quality_distribution": {"high": 3},
            },
            "intelligence": {
                "dominant_pattern": "front-pressure conversions",
                "tactical_identity": "Adaptive Forecourt Aggressor",
                "momentum_state": "surging",
                "recommended_focus": ["recovery-into-pressure", "front-court-hold timing"],
            },
            "sequence_memory": {
                "memory_summary": "The match keeps returning to recovery-led forecourt pressure patterns.",
                "sequence_tags": ["front-pressure", "tempo-assertive"],
            },
            "duel_summary": {
                "duel_edge": "user",
                "projected_edge_score": 0.23,
            },
            "replay_story": {
                "title": "Recovery Built the Advantage",
                "chapters": [
                    "Early rallies established structure through deep recovery.",
                    "Forecourt holds then converted that stability into pressure.",
                ],
            },
            "report": {
                "headline": "Demo Match Report",
                "narrative": "The match shows a stable progression from recovery control into front-court pressure.",
            },
        },
        "timeline": timeline,
        "warnings": [],
    }


def build_demo_catalog() -> Dict[str, Any]:
    return {
        "rally_demo": {
            "path": "/demo/rally",
            "description": "Returns a full rally analysis payload for frontend integration and documentation.",
        },
        "match_demo": {
            "path": "/demo/match",
            "description": "Returns a multi-rally match payload with metrics, report blocks, and replay story.",
        },
        "telemetry_summary": {
            "path": "/telemetry/summary",
            "description": "Summarizes recently captured request and analysis events.",
        },
    }
