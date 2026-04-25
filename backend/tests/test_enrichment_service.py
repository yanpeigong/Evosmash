from services.enrichment_service import build_summary_payload, normalize_advice_payload


def test_normalize_advice_payload_uses_tactic_fallbacks():
    state = {"attack_phase": "under_pressure", "event": "Pressure Rally"}
    tactics = [
        {
            "name": "Front Court Hold",
            "recommended_action": "Recover early and hold the net.",
            "confidence_label": "high",
        }
    ]

    payload = normalize_advice_payload(None, tactics, state)

    assert payload["headline"] == "Lean into Front Court Hold"
    assert payload["next_step"] == "Recover early and hold the net."
    assert payload["confidence_label"] == "high"


def test_build_summary_payload_reflects_loss_verdict():
    state = {"attack_phase": "neutral", "shot_shape": "balanced-rally"}
    advice = {"focus": "Recovery", "confidence_label": "medium"}
    tactics = [{"name": "Deep Clear Reset", "confidence_label": "medium"}]

    summary = build_summary_payload(state, advice, tactics, "LOSS")

    assert summary["headline"] == "Pressure response needs work"
    assert summary["verdict"] == "LOSS"
    assert "Deep Clear Reset" in summary["key_takeaway"]
