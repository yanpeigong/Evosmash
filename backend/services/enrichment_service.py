from typing import Dict, List


def _confidence_label(score: float, expected_win_rate: float) -> str:
    if score >= 0.78 or expected_win_rate >= 72:
        return "high"
    if score <= 0.48 or expected_win_rate <= 45:
        return "low"
    return "medium"


def _format_action_from_content(content: str) -> str:
    if not content:
        return "Reset and prepare for the next exchange."
    sentence = content.split(".")[0].strip()
    return sentence if sentence.endswith(".") else f"{sentence}."


def _build_why_this_tactic(name: str, event_name: str, speed: float, expected_win_rate: float, confidence_label: str, rank: int) -> str:
    rank_context = "the clearest match" if rank == 1 else f"a strong supporting option at rank {rank}"
    confidence_context = {
        "high": "with strong historical support",
        "medium": "with a balanced confidence level",
        "low": "as an exploratory alternative",
    }.get(confidence_label, "with balanced confidence")
    return (
        f"{name} is {rank_context} for this {event_name} pattern at {speed:.1f} km/h, "
        f"projecting a {expected_win_rate:.1f}% expected win rate {confidence_context}."
    )


def _build_risk_note(event_name: str, speed: float, confidence_label: str, expected_win_rate: float) -> str:
    if confidence_label == "low":
        return "This option is more exploratory, so be ready to recover quickly if the opponent reads it early."
    if speed >= 200:
        return f"The pace is very high for a {event_name} situation, so timing and contact quality are critical."
    if expected_win_rate < 55:
        return "The tactical edge is modest, so execution quality matters more than the pattern itself."
    return "This choice is reliable, but it still depends on early preparation and clean footwork into the shot."



def enrich_tactics(state: Dict, tactics: List[Dict]) -> List[Dict]:
    enriched = []
    event_name = state.get("event", "Rally").lower()
    speed = state.get("max_speed_kmh", 0.0)

    for index, tactic in enumerate(tactics, start=1):
        expected_win_rate = float(tactic.get("expected_win_rate", 50.0))
        score = float(tactic.get("score", 0.0))
        name = tactic.get("name") or tactic.get("content") or f"Tactic {index}"
        recommended_action = _format_action_from_content(tactic.get("content", name))
        confidence_label = _confidence_label(score, expected_win_rate)

        rank_hint = "top recommendation" if index == 1 else f"ranked option #{index}"
        reason = (
            f"{name} is the {rank_hint} because it fits a {event_name} scenario at "
            f"{speed:.1f} km/h and carries an expected win rate of {expected_win_rate:.1f}%."
        )
        why_this_tactic = _build_why_this_tactic(
            name=name,
            event_name=event_name,
            speed=speed,
            expected_win_rate=expected_win_rate,
            confidence_label=confidence_label,
            rank=index,
        )
        risk_note = _build_risk_note(
            event_name=event_name,
            speed=speed,
            confidence_label=confidence_label,
            expected_win_rate=expected_win_rate,
        )

        enriched.append(
            {
                **tactic,
                "name": name,
                "recommended_action": recommended_action,
                "confidence_label": confidence_label,
                "reason": reason,
                "why_this_tactic": why_this_tactic,
                "risk_note": risk_note,
            }
        )

    return enriched



def normalize_advice_payload(raw_advice, tactics: List[Dict], state: Dict) -> Dict:
    if isinstance(raw_advice, dict):
        text = raw_advice.get("text") or "Stay balanced and prepare early."
        headline = raw_advice.get("headline") or "Stay composed"
        focus = raw_advice.get("focus") or "Recovery"
        next_step = raw_advice.get("next_step") or "Prepare for the next shot."
        confidence_label = raw_advice.get("confidence_label") or (
            tactics[0].get("confidence_label", "medium") if tactics else "medium"
        )
        source = raw_advice.get("source") or "llm"
    else:
        text = str(raw_advice or "Stay balanced and prepare early.")
        top_tactic = tactics[0]["name"] if tactics else state.get("event", "Rally")
        headline = f"Lean into {top_tactic}"
        focus = "Shot selection"
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

    if verdict == "WIN":
        headline = "Winning pattern detected"
    elif verdict == "LOSS":
        headline = "Pressure response needs work"
    else:
        headline = "Rally pattern captured"

    key_takeaway = (
        f"Primary tactical direction: {top_tactic}. "
        f"Focus on {advice.get('focus', 'shot selection').lower()} in the next exchange."
    )

    return {
        "headline": headline,
        "verdict": verdict,
        "confidence_label": confidence_label,
        "key_takeaway": key_takeaway,
    }



def build_diagnostics_payload(
    warnings: List[str],
    pipeline_status: Dict[str, str],
    motion_feedback: str,
    trajectory_points: int,
    tactics: List[Dict],
) -> Dict:
    if warnings:
        analysis_quality = "degraded" if len(warnings) > 1 else "limited"
    elif trajectory_points < 8:
        analysis_quality = "low"
    elif tactics and tactics[0].get("confidence_label") == "high":
        analysis_quality = "high"
    else:
        analysis_quality = "medium"

    return {
        "warnings": warnings,
        "pipeline": pipeline_status,
        "motion_feedback": motion_feedback,
        "trajectory_points": trajectory_points,
        "analysis_quality": analysis_quality,
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
        "pipeline": {
            "tracking": "failed",
            "pose": "skipped",
            "physics": "skipped",
            "retrieval": "skipped",
            "coach": "fallback",
        },
        "motion_feedback": "Unavailable",
        "trajectory_points": 0,
        "analysis_quality": "degraded",
    }
    return {
        "physics": {
            "event": "Unknown",
            "max_speed_kmh": 0.0,
            "description": "Analysis could not be completed for this clip.",
            "coordinates": [],
            "auto_result": "UNKNOWN",
            "match_type": match_type,
        },
        "advice": advice,
        "tactics": [],
        "session_id": None,
        "match_type": match_type,
        "auto_result": "UNKNOWN",
        "auto_reward": 0.0,
        "summary": summary,
        "diagnostics": diagnostics,
    }
