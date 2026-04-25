import logging

import main


def test_system_status_endpoint_returns_runtime_details(client):
    response = client.get("/system/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["analysis_ready"] is True
    assert payload["app"]["title"] == "EvoSmash Backend"
    assert "loaded_env_file" in payload["config"]


def test_analyze_rally_returns_stubbed_payload(client, video_upload):
    response = client.post("/analyze_rally", files=video_upload, data={"match_type": "singles"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["auto_result"] == "WIN"
    assert payload["match_type"] == "singles"
    assert payload["diagnostics"]["analysis_quality"] == "high"
    assert "X-Request-ID" in response.headers


def test_analyze_match_returns_metrics(client, video_upload):
    response = client.post("/analyze_match", files=video_upload, data={"match_type": "doubles"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["match_summary"]["valid_rallies_analyzed"] == 2
    assert payload["match_summary"]["metrics"]["peak_speed_kmh"] == 121.0


def test_analyze_rally_rejects_invalid_match_type(client, video_upload):
    response = client.post("/analyze_rally", files=video_upload, data={"match_type": "training"})

    assert response.status_code == 400
    assert response.json()["detail"] == "match_type must be 'singles' or 'doubles'."


def test_analyze_rally_requires_available_runtime(unavailable_client, video_upload):
    response = unavailable_client.post("/analyze_rally", files=video_upload, data={"match_type": "singles"})

    assert response.status_code == 503
    payload = response.json()["detail"]
    assert payload["system_status"]["analysis_ready"] is False


def test_feedback_endpoint_updates_policy(client):
    response = client.post("/feedback", data={"tactic_id": "tactic-1", "result": "WIN"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["reward"] == 10.0
    assert payload["policy_update"]["tactic_id"] == "tactic-1"


def test_analysis_logging_emits_request_and_response_records(client, video_upload, caplog):
    original_propagate = main.logger.propagate
    main.logger.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger="evosmash"):
            response = client.post("/analyze_rally", files=video_upload, data={"match_type": "singles"})
    finally:
        main.logger.propagate = original_propagate

    assert response.status_code == 200
    messages = [record.getMessage() for record in caplog.records]
    assert any("event=request.started" in message for message in messages)
    assert any("event=analysis.request" in message for message in messages)
    assert any("event=analysis.response" in message for message in messages)
    assert any("event=request.completed" in message for message in messages)
