from typing import Dict, List


def _confidence_label(score: float, expected_win_rate: float, context_score: float = 0.5, risk_penalty: float = 0.0) -> str:
    composite = 0.45 * score + 0.3 * (expected_win_rate / 100.0) + 0.25 * context_score - 0.15 * risk_penalty
    if composite >= 0.76 or expected_win_rate >= 74:
        return "high"
    if composite <= 0.5 or expected_win_rate <= 45:
        return "low"
    return "medium"


def _format_action_from_content(content: str) -> str:
    if not content:
        return "Reset and prepare for the next exchange."
    sentence = content.split(".")[0].strip()
    return sentence if sentence.endswith(".") else f"{sentence}."


def _build_why_this_tactic(name: str, event_name: str, speed: float, expected_win_rate: float, confidence_label: str, rank: int, attack_phase: str, court_context: str, style_family: str) -> str:
    rank_context = "the clearest match" if rank == 1 else f"a strong supporting option at rank {rank}"
    confidence_context = {"high": "with strong historical support", "medium": "with balanced confidence", "low": "as an exploratory alternative"}.get(confidence_label, "with balanced confidence")
    return (
        f"{name} is {rank_context} for this {event_name} pattern at {speed:.1f} km/h, "
        f"fitting a {attack_phase} phase in {court_context} through a {style_family} response and projecting "
        f"a {expected_win_rate:.1f}% expected win rate {confidence_context}."
    )


def _build_risk_note(event_name: str, speed: float, confidence_label: str, expected_win_rate: float, risk_level: str, attack_phase: str) -> str:
    if risk_level == "high" and attack_phase == "under_pressure":
        return "This is a high-commitment option under pressure, so only take it if your base is already stable."
    if confidence_label == "low":
        return "This option is more exploratory, so be ready to recover quickly if the opponent reads it early."
    if speed >= 200:
        return f"The pace is very high for a {event_name} situation, so timing and contact quality are critical."
    if expected_win_rate < 55:
        return "The tactical edge is modest, so execution quality matters more than the pattern itself."
    return "This choice is reliable, but it still depends on early preparation and clean footwork into the shot."


def enrich_tactics(state: Dict, tactics: List[Dict]) -> List[Dict]:
    enriched = []
    event_name = state.get("event", "Rally")
    speed = state.get("max_speed_kmh", 0.0)
    attack_phase = state.get("attack_phase", "neutral")
    court_context = state.get("court_context", "unknown")

    for index, tactic in enumerate(tactics, start=1):
        expected_win_rate = float(tactic.get("expected_win_rate", 50.0))
        ranking_score = float(tactic.get("rerank_score", tactic.get("score", 0.0)) or 0.0)
        context_score = float(tactic.get("context_score", 0.5))
        risk_penalty = float(tactic.get("risk_penalty", 0.0))
        metadata = tactic.get("metadata", {})
        name = tactic.get("name") or tactic.get("content") or f"Tactic {index}"
        recommended_action = _format_action_from_content(tactic.get("content", name))
        confidence_label = _confidence_label(ranking_score, expected_win_rate, context_score, risk_penalty)
        style_family = metadata.get("style_family", "balanced")
        risk_level = metadata.get("risk_level", "medium")

        rank_hint = "top recommendation" if index == 1 else f"ranked option #{index}"
        reason = f"{name} is the {rank_hint} because it fits a {event_name.lower()} scenario at {speed:.1f} km/h with {attack_phase} phase alignment and an expected win rate of {expected_win_rate:.1f}%."
        why_this_tactic = _build_why_this_tactic(name, event_name.lower(), speed, expected_win_rate, confidence_label, index, attack_phase.replace("_", " "), court_context.replace("_", " "), style_family.replace("-", " "))
        risk_note = _build_risk_note(event_name, speed, confidence_label, expected_win_rate, risk_level, attack_phase)

        enriched.append(
            {
                **tactic,
                "name": name,
                "recommended_action": recommended_action,
                "confidence_label": confidence_label,
                "reason": reason,
                "why_this_tactic": why_this_tactic,
                "risk_note": risk_note,
                "fit_breakdown": tactic.get("fit_breakdown", {}),
                "selection_profile": tactic.get("selection_profile", {}),
                "scenario_summary": tactic.get("scenario_summary", {}),
                "related_tactics": tactic.get("related_tactics", []),
                "transition_family": tactic.get("transition_family", "isolated"),
                "rerank_score": tactic.get("rerank_score", tactic.get("score", 0.0)),
                "continuity_score": tactic.get("continuity_score", 0.0),
                "coverage_score": tactic.get("coverage_score", 0.0),
                "volatility_guard": tactic.get("volatility_guard", 0.0),
                "novelty_bonus": tactic.get("novelty_bonus", 0.0),
                "rank_reason": tactic.get("rank_reason", ""),
                "frontier_hint": tactic.get("frontier_hint", ""),
                "evolution_replay": tactic.get("evolution_replay", {}),
            }
        )

    return enriched


def normalize_advice_payload(raw_advice, tactics: List[Dict], state: Dict) -> Dict:
    if isinstance(raw_advice, dict):
        text = raw_advice.get("text") or "Stay balanced and prepare early."
        headline = raw_advice.get("headline") or "Stay composed"
        focus = raw_advice.get("focus") or "Recovery"
        next_step = raw_advice.get("next_step") or "Prepare for the next shot."
        confidence_label = raw_advice.get("confidence_label") or (tactics[0].get("confidence_label", "medium") if tactics else "medium")
        source = raw_advice.get("source") or "llm"
    else:
        text = str(raw_advice or "Stay balanced and prepare early.")
        top_tactic = tactics[0]["name"] if tactics else state.get("event", "Rally")
        headline = f"Lean into {top_tactic}"
        focus = state.get("attack_phase", "shot selection").replace("_", " ").title()
        next_step = tactics[0].get("recommended_action", "Prepare for the next shot.") if tactics else "Prepare for the next shot."
        confidence_label = tactics[0].get("confidence_label", "medium") if tactics else "medium"
        source = "fallback"

    return {
        "text": text,
        "headline": headline,
        "focus": focus,
        "next_step": next_step,
        "confidence_label": confidence_label,
        "source": source,
    }


def build_summary_payload(state: Dict, advice: Dict, tactics: List[Dict], auto_result: str) -> Dict:
    top_tactic = tactics[0]["name"] if tactics else "Neutral reset"
    confidence_label = advice.get("confidence_label", tactics[0].get("confidence_label", "medium") if tactics else "medium")
    verdict = auto_result or "UNKNOWN"
    attack_phase = state.get("attack_phase", "neutral").replace("_", " ")
    shot_shape = state.get("shot_shape", "balanced rally").replace("-", " ")

    if verdict == "WIN":
        headline = "Winning pattern detected"
    elif verdict == "LOSS":
        headline = "Pressure response needs work"
    else:
        headline = "Rally pattern captured"

    key_takeaway = f"Primary tactical direction: {top_tactic}. Current phase reads as {attack_phase} with a {shot_shape} shot pattern, so focus on {advice.get('focus', 'shot selection').lower()} next."
    return {"headline": headline, "verdict": verdict, "confidence_label": confidence_label, "key_takeaway": key_takeaway}


def build_diagnostics_payload(warnings: List[str], pipeline_status: Dict[str, str], motion_feedback: str, trajectory_points: int, tactics: List[Dict], state: Dict = None, tracker_diagnostics: Dict = None, motion_profile: Dict = None, rally_quality: Dict = None, confidence_report: Dict = None, referee_audit: Dict = None, sequence_context: Dict = None, duel_projection: Dict = None) -> Dict:
    state = state or {}
    tracker_diagnostics = tracker_diagnostics or {}
    motion_profile = motion_profile or {}
    rally_quality = rally_quality or {}
    confidence_report = confidence_report or {}
    referee_audit = referee_audit or {}
    sequence_context = sequence_context or {}
    duel_projection = duel_projection or {}

    if warnings:
        analysis_quality = "degraded" if len(warnings) > 1 else "limited"
    elif trajectory_points < 8:
        analysis_quality = "low"
    elif rally_quality.get("overall_quality", 0.0) >= 0.76:
        analysis_quality = "high"
    else:
        analysis_quality = "medium"

    retrieval_summary = {}
    if tactics:
        top = tactics[0]
        metadata = top.get("metadata", {})
        retrieval_summary = {
            "selected_tactic": top.get("name", "Unknown"),
            "score": round(float(top.get("score", 0.0)), 3),
            "rerank_score": round(float(top.get("rerank_score", top.get("score", 0.0)) or 0.0), 3),
            "expected_win_rate": round(float(top.get("expected_win_rate", 50.0)), 2),
            "style_family": metadata.get("style_family", "balanced"),
            "phase_preference": metadata.get("phase_preference", "neutral"),
            "tempo_band": metadata.get("tempo_band", "medium"),
            "risk_level": metadata.get("risk_level", "medium"),
            "fit_breakdown": top.get("fit_breakdown", {}),
            "scenario_summary": top.get("scenario_summary", {}),
            "transition_family": top.get("transition_family", "isolated"),
            "rank_reason": top.get("rank_reason", ""),
            "frontier_hint": top.get("frontier_hint", ""),
            "development_stage": (top.get("evolution_replay", {}) or {}).get("development_stage", "stabilize"),
        }

    combined_warnings = list(warnings)
    combined_warnings.extend(rally_quality.get("warnings", []))

    return {
        "warnings": combined_warnings,
        "pipeline": pipeline_status,
        "motion_feedback": motion_feedback,
        "trajectory_points": trajectory_points,
        "analysis_quality": analysis_quality,
        "retrieval_summary": retrieval_summary,
        "physics_profile": {
            "attack_phase": state.get("attack_phase", "neutral"),
            "tempo_profile": state.get("tempo_profile", "medium"),
            "shot_shape": state.get("shot_shape", "balanced-rally"),
            "pressure_index": state.get("pressure_index", 0.0),
        },
        "tracker_diagnostics": tracker_diagnostics,
        "motion_profile": motion_profile,
        "rally_quality": rally_quality,
        "confidence_report": confidence_report,
        "referee_audit": referee_audit,
        "sequence_context": sequence_context,
        "duel_projection": duel_projection,
    }


def make_empty_rally_response(match_type: str, warning: str) -> Dict:
    advice = {
        "text": "The clip could not be analyzed reliably. Try a clearer rally angle or a slightly longer clip.",
        "headline": "Analysis incomplete",
        "focus": "Capture quality",
        "next_step": "Upload a steadier rally clip with the full shuttle path visible.",
        "confidence_label": "low",
        "source": "fallback",
    }
    summary = {
        "headline": "Insufficient rally signal",
        "verdict": "UNKNOWN",
        "confidence_label": "low",
        "key_takeaway": "The current clip does not contain enough reliable signal for tactical analysis.",
    }
    diagnostics = {
        "warnings": [warning],
        "pipeline": {"tracking": "failed", "pose": "skipped", "physics": "skipped", "retrieval": "skipped", "coach": "fallback"},
        "motion_feedback": "Unavailable",
        "trajectory_points": 0,
        "analysis_quality": "degraded",
        "retrieval_summary": {},
        "physics_profile": {"attack_phase": "neutral", "tempo_profile": "medium", "shot_shape": "balanced-rally", "pressure_index": 0.0},
        "tracker_diagnostics": {},
        "motion_profile": {},
        "rally_quality": {},
        "confidence_report": {},
        "referee_audit": {},
        "sequence_context": {},
        "duel_projection": {},
    }
    return {
        "physics": {"event": "Unknown", "max_speed_kmh": 0.0, "description": "Analysis could not be completed for this clip.", "coordinates": [], "auto_result": "UNKNOWN", "match_type": match_type},
        "advice": advice,
        "tactics": [],
        "session_id": None,
        "match_type": match_type,
        "auto_result": "UNKNOWN",
        "auto_reward": 0.0,
        "summary": summary,
        "diagnostics": diagnostics,
        "report": {},
    }
