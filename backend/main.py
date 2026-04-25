import os
import shutil
import time
import uuid
from typing import Any, Dict, List

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from config import (
    ALLOWED_VIDEO_EXTENSIONS,
    API_HOST,
    API_PORT,
    CORS_ALLOW_ORIGINS,
    LOG_LEVEL,
    MAX_UPLOAD_SIZE_MB,
    TEMP_DIR,
    describe_runtime_config,
)
from core.utils.logging_utils import configure_logging, log_event
from schemas.analysis_response import MatchAnalysisResponse, RallyAnalysisResponse
from schemas.system_status import DemoCatalogPayload, SystemStatusPayload, TelemetrySnapshotPayload
from services import (
    TelemetryService,
    bootstrap_runtime,
    build_demo_catalog,
    build_demo_match_payload,
    build_demo_rally_payload,
)

logger = configure_logging(LOG_LEVEL)


def build_starting_status() -> Dict[str, Any]:
    return {
        "status": "starting",
        "analysis_ready": False,
        "components": {},
        "summary": {"ready": 0, "fallback": 0, "failed": 0},
        "insights": {
            "component_order": [],
            "healthy_components": [],
            "degraded_components": [],
            "critical_components": [],
            "component_matrix": [],
        },
    }


def get_runtime_status(runtime) -> Dict[str, Any]:
    if runtime is None:
        return build_starting_status()
    return runtime.build_status_payload()


def get_runtime(request: Request):
    return getattr(request.app.state, "runtime", None)


def get_telemetry(request: Request):
    return getattr(request.app.state, "telemetry", None)


def validate_match_type(match_type: str) -> str:
    if match_type not in {"singles", "doubles"}:
        raise HTTPException(status_code=400, detail="match_type must be 'singles' or 'doubles'.")
    return match_type


def _uploaded_file_size(file: UploadFile) -> int:
    current_position = file.file.tell()
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(current_position, os.SEEK_SET)
    return size


def validate_upload(file: UploadFile) -> None:
    suffix = os.path.splitext(file.filename or "")[1].lower()
    content_type = (file.content_type or "").lower()
    if suffix and suffix not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")
    if not suffix and not content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a supported video format.")

    file_size = _uploaded_file_size(file)
    if file_size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file is too large. Limit is {MAX_UPLOAD_SIZE_MB} MB.",
        )

    file.file.seek(0)


def ensure_analysis_available(request: Request) -> None:
    runtime = get_runtime(request)
    if runtime is None or runtime.analysis_service is None:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Analysis pipeline is unavailable because critical components failed to load.",
                "system_status": get_runtime_status(runtime),
            },
        )


def _save_upload_to_temp(file: UploadFile, prefix: str = "") -> str:
    filename = file.filename or "upload.mp4"
    suffix = os.path.splitext(filename)[1].lower() or ".mp4"
    filepath = os.path.join(TEMP_DIR, f"{prefix}{uuid.uuid4()}{suffix}")
    with open(filepath, "wb") as output_file:
        shutil.copyfileobj(file.file, output_file)
    file.file.seek(0)
    return filepath


def _log_analysis_request(request: Request, endpoint: str, file: UploadFile, match_type: str) -> None:
    size_bytes = _uploaded_file_size(file)
    telemetry = get_telemetry(request)
    if telemetry is not None:
        telemetry.record_analysis_request(
            request_id=getattr(request.state, "request_id", ""),
            endpoint=endpoint,
            match_type=match_type,
            filename=file.filename or "unknown",
            size_bytes=size_bytes,
        )
    log_event(
        logger,
        "analysis.request",
        request_id=getattr(request.state, "request_id", ""),
        endpoint=endpoint,
        match_type=match_type,
        filename=file.filename or "unknown",
        content_type=file.content_type or "unknown",
        size_bytes=size_bytes,
    )


def _log_analysis_response(request: Request, endpoint: str, payload: Dict[str, Any]) -> None:
    telemetry = get_telemetry(request)
    if telemetry is not None:
        telemetry.record_analysis_response(
            request_id=getattr(request.state, "request_id", ""),
            endpoint=endpoint,
            payload=payload,
        )
    if endpoint == "analyze_rally":
        diagnostics = payload.get("diagnostics", {}) or {}
        log_event(
            logger,
            "analysis.response",
            request_id=getattr(request.state, "request_id", ""),
            endpoint=endpoint,
            auto_result=payload.get("auto_result", "UNKNOWN"),
            tactic_count=len(payload.get("tactics", []) or []),
            analysis_quality=diagnostics.get("analysis_quality", "unknown"),
            warning_count=len(diagnostics.get("warnings", []) or []),
        )
        return

    match_summary = payload.get("match_summary", {}) or {}
    metrics = match_summary.get("metrics", {}) or {}
    log_event(
        logger,
        "analysis.response",
        request_id=getattr(request.state, "request_id", ""),
        endpoint=endpoint,
        status=payload.get("status", "unknown"),
        valid_rallies=match_summary.get("valid_rallies_analyzed", 0),
        total_rallies=match_summary.get("total_rallies_found", 0),
        peak_speed_kmh=metrics.get("peak_speed_kmh", 0.0),
    )


def _build_runtime_notes(runtime) -> List[str]:
    if runtime is None:
        return [
            "Runtime has not bootstrapped yet.",
            "The backend can still expose static demo payloads before analysis components finish loading.",
        ]

    status_payload = runtime.build_status_payload()
    notes = [
        f"Overall runtime status is {status_payload.get('status', 'unknown')}.",
        f"Analysis ready: {status_payload.get('analysis_ready', False)}.",
        f"Readiness score: {(status_payload.get('summary', {}) or {}).get('readiness_score', 0.0)}.",
    ]
    degraded_components = ((status_payload.get("insights", {}) or {}).get("degraded_components", []))[:4]
    if degraded_components:
        notes.append(f"Degraded components detected: {', '.join(degraded_components)}.")
    else:
        notes.append("No degraded runtime components are currently reported.")
    return notes


def _build_api_catalog() -> Dict[str, Any]:
    return {
        "core_endpoints": [
            {"path": "/", "method": "GET", "purpose": "Lightweight root status."},
            {"path": "/health", "method": "GET", "purpose": "Health payload for deployment probes."},
            {"path": "/system/status", "method": "GET", "purpose": "Expanded runtime and config view."},
            {"path": "/analyze_rally", "method": "POST", "purpose": "Analyze one badminton rally clip."},
            {"path": "/analyze_match", "method": "POST", "purpose": "Analyze a full match clip and segment rallies."},
            {"path": "/feedback", "method": "POST", "purpose": "Submit reward feedback for tactic evolution."},
        ],
        "support_endpoints": [
            {"path": "/telemetry/summary", "method": "GET", "purpose": "Recent request and analysis telemetry."},
            {"path": "/telemetry/recent", "method": "GET", "purpose": "Recent events with optional limit controls."},
            {"path": "/demo/catalog", "method": "GET", "purpose": "Frontend-safe demo endpoint catalog."},
            {"path": "/demo/rally", "method": "GET", "purpose": "Static rally analysis demo payload."},
            {"path": "/demo/match", "method": "GET", "purpose": "Static match analysis demo payload."},
        ],
    }


def create_app(runtime_override=None) -> FastAPI:
    app = FastAPI(title="EvoSmash Backend", version="1.1.0")
    app.state.runtime = runtime_override
    app.state.telemetry = TelemetryService()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def startup_event():
        if app.state.runtime is None:
            log_event(logger, "system.initializing")
            app.state.runtime = bootstrap_runtime()

        status_payload = get_runtime_status(app.state.runtime)
        log_event(
            logger,
            "system.ready",
            status=status_payload.get("status", "unknown"),
            analysis_ready=status_payload.get("analysis_ready", False),
            readiness_score=(status_payload.get("summary", {}) or {}).get("readiness_score", 0.0),
        )

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        started_at = time.perf_counter()
        telemetry = get_telemetry(request)
        client_host = request.client.host if request.client else "unknown"

        if telemetry is not None:
            telemetry.record_request_started(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                client=client_host,
            )

        log_event(
            logger,
            "request.started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client=client_host,
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            if telemetry is not None:
                telemetry.record_request_failed(
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    duration_ms=duration_ms,
                )
            log_event(
                logger,
                "request.failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
            )
            raise

        response.headers["X-Request-ID"] = request_id
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        if telemetry is not None:
            telemetry.record_request_completed(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
        log_event(
            logger,
            "request.completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    @app.get("/")
    async def root(request: Request):
        status_payload = get_runtime_status(get_runtime(request))
        return {
            "status": status_payload["status"],
            "analysis_ready": status_payload["analysis_ready"],
            "message": "EvoSmash Backend is ready!",
        }

    @app.get("/health")
    async def health(request: Request):
        payload = get_runtime_status(get_runtime(request))
        payload["config"] = {
            "max_upload_size_mb": describe_runtime_config()["max_upload_size_mb"],
            "llm_enabled": describe_runtime_config()["llm"]["enabled"],
            "loaded_env_file": describe_runtime_config()["loaded_env_file"],
        }
        return payload

    @app.get("/system/status", response_model=SystemStatusPayload)
    async def system_status(request: Request):
        payload = get_runtime_status(get_runtime(request))
        payload["config"] = describe_runtime_config()
        payload["app"] = {
            "title": request.app.title,
            "version": request.app.version,
            "runtime_notes": _build_runtime_notes(get_runtime(request)),
            "api_catalog": _build_api_catalog(),
        }
        return payload

    @app.get("/telemetry/summary", response_model=TelemetrySnapshotPayload)
    async def telemetry_summary(request: Request):
        telemetry = get_telemetry(request)
        if telemetry is None:
            return {"summary": {}, "recent_requests": [], "recent_analysis_events": [], "recent_feedback_events": []}
        return telemetry.export_snapshot()

    @app.get("/telemetry/recent")
    async def telemetry_recent(request: Request, request_limit: int = 20, analysis_limit: int = 20, feedback_limit: int = 10):
        telemetry = get_telemetry(request)
        if telemetry is None:
            return {"recent_requests": [], "recent_analysis_events": [], "recent_feedback_events": []}
        return {
            "recent_requests": telemetry.recent_requests(limit=request_limit),
            "recent_analysis_events": telemetry.recent_analysis_events(limit=analysis_limit),
            "recent_feedback_events": telemetry.recent_feedback_events(limit=feedback_limit),
        }

    @app.get("/demo/catalog", response_model=DemoCatalogPayload)
    async def demo_catalog():
        return build_demo_catalog()

    @app.get("/demo/rally", response_model=RallyAnalysisResponse)
    async def demo_rally(match_type: str = "singles"):
        match_type = validate_match_type(match_type)
        return build_demo_rally_payload(match_type=match_type)

    @app.get("/demo/match", response_model=MatchAnalysisResponse)
    async def demo_match(match_type: str = "singles"):
        match_type = validate_match_type(match_type)
        return build_demo_match_payload(match_type=match_type)

    @app.post("/analyze_rally", response_model=RallyAnalysisResponse)
    async def analyze_rally(request: Request, file: UploadFile = File(...), match_type: str = Form("singles")):
        ensure_analysis_available(request)
        match_type = validate_match_type(match_type)
        validate_upload(file)
        _log_analysis_request(request, "analyze_rally", file, match_type)

        filepath = _save_upload_to_temp(file)

        try:
            payload = request.app.state.runtime.analysis_service.analyze_rally(filepath, match_type)
            _log_analysis_response(request, "analyze_rally", payload)
            return payload
        except HTTPException:
            raise
        except Exception as error:
            log_event(
                logger,
                "analysis.error",
                request_id=getattr(request.state, "request_id", ""),
                endpoint="analyze_rally",
                error=str(error),
            )
            raise HTTPException(status_code=500, detail=str(error))
        finally:
            await file.close()
            if os.path.exists(filepath):
                os.remove(filepath)

    @app.post("/analyze_match", response_model=MatchAnalysisResponse)
    async def analyze_match(request: Request, file: UploadFile = File(...), match_type: str = Form("singles")):
        ensure_analysis_available(request)
        match_type = validate_match_type(match_type)
        validate_upload(file)
        _log_analysis_request(request, "analyze_match", file, match_type)

        filepath = _save_upload_to_temp(file, prefix="match_")

        try:
            payload = request.app.state.runtime.analysis_service.analyze_match(filepath, match_type)
            _log_analysis_response(request, "analyze_match", payload)
            return payload
        except Exception as error:
            log_event(
                logger,
                "analysis.error",
                request_id=getattr(request.state, "request_id", ""),
                endpoint="analyze_match",
                error=str(error),
            )
            raise HTTPException(status_code=500, detail=str(error))
        finally:
            await file.close()
            if os.path.exists(filepath):
                os.remove(filepath)

    @app.post("/feedback")
    async def feedback(request: Request, tactic_id: str = Form(...), result: str = Form(...)):
        runtime = get_runtime(request)
        if runtime is None or runtime.physics is None:
            raise HTTPException(status_code=503, detail="Physics engine is unavailable.")

        reward = runtime.physics.calculate_reward(result)
        policy_update = runtime.rag.update_policy(tactic_id, reward, context={"auto_result": result}) or {}
        telemetry = get_telemetry(request)
        if telemetry is not None:
            telemetry.record_feedback(
                request_id=getattr(request.state, "request_id", ""),
                tactic_id=tactic_id,
                result=result,
                reward=reward,
            )
        log_event(
            logger,
            "feedback.processed",
            request_id=getattr(request.state, "request_id", ""),
            tactic_id=tactic_id,
            result=result,
            reward=reward,
        )
        return {"status": "ok", "reward": reward, "policy_update": policy_update}

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("main:app", host=API_HOST, port=API_PORT, reload=False)
