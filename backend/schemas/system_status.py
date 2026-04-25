from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ComponentStatusPayload(BaseModel):
    status: str = "unknown"
    class_name: Optional[str] = None
    detail: str = ""
    critical: bool = False
    readiness_score: float = 0.0
    tags: List[str] = Field(default_factory=list)


class RuntimeSummaryPayload(BaseModel):
    ready: int = 0
    fallback: int = 0
    failed: int = 0
    readiness_score: float = 0.0
    critical_failures: List[str] = Field(default_factory=list)


class RuntimeInsightsPayload(BaseModel):
    component_order: List[str] = Field(default_factory=list)
    healthy_components: List[str] = Field(default_factory=list)
    degraded_components: List[str] = Field(default_factory=list)
    critical_components: List[str] = Field(default_factory=list)
    component_matrix: List[Dict[str, Any]] = Field(default_factory=list)


class SystemStatusPayload(BaseModel):
    status: str = "starting"
    analysis_ready: bool = False
    components: Dict[str, ComponentStatusPayload] = Field(default_factory=dict)
    summary: RuntimeSummaryPayload = Field(default_factory=RuntimeSummaryPayload)
    insights: RuntimeInsightsPayload = Field(default_factory=RuntimeInsightsPayload)
    config: Dict[str, Any] = Field(default_factory=dict)
    app: Dict[str, Any] = Field(default_factory=dict)


class TelemetrySummaryPayload(BaseModel):
    request_log_capacity: int = 0
    analysis_event_capacity: int = 0
    request_events_stored: int = 0
    analysis_events_stored: int = 0
    feedback_events_stored: int = 0
    request_stage_distribution: Dict[str, int] = Field(default_factory=dict)
    analysis_endpoint_distribution: Dict[str, int] = Field(default_factory=dict)
    analysis_result_distribution: Dict[str, int] = Field(default_factory=dict)
    average_completed_request_ms: float = 0.0
    latest_request_id: Optional[str] = None


class TelemetrySnapshotPayload(BaseModel):
    summary: TelemetrySummaryPayload = Field(default_factory=TelemetrySummaryPayload)
    recent_requests: List[Dict[str, Any]] = Field(default_factory=list)
    recent_analysis_events: List[Dict[str, Any]] = Field(default_factory=list)
    recent_feedback_events: List[Dict[str, Any]] = Field(default_factory=list)


class DemoCatalogPayload(BaseModel):
    rally_demo: Dict[str, Any] = Field(default_factory=dict)
    match_demo: Dict[str, Any] = Field(default_factory=dict)
    telemetry_summary: Dict[str, Any] = Field(default_factory=dict)
