from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SessionTagPayload(BaseModel):
    label: str
    weight: float = 0.0
    category: str = "general"
    description: str = ""


class SessionNotePayload(BaseModel):
    note_id: str
    created_at: str
    author: str = "system"
    note_type: str = "summary"
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionBookmarkPayload(BaseModel):
    bookmark_id: str
    title: str
    created_at: str
    rally_index: Optional[int] = None
    timeline_position: Optional[float] = None
    description: str = ""
    tags: List[str] = Field(default_factory=list)


class SessionArtifactPayload(BaseModel):
    artifact_id: str
    artifact_type: str = "report"
    title: str
    created_at: str
    path: str = ""
    mime_type: str = "application/json"
    size_bytes: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionTrendPayload(BaseModel):
    label: str
    score: float = 0.0
    slope: float = 0.0
    confidence: float = 0.0
    direction: str = "flat"
    evidence: List[str] = Field(default_factory=list)


class SessionFocusPayload(BaseModel):
    label: str
    priority: str = "medium"
    confidence: float = 0.0
    rationale: str = ""
    drills: List[str] = Field(default_factory=list)
    guardrails: List[str] = Field(default_factory=list)


class SessionSnapshotPayload(BaseModel):
    snapshot_id: str
    created_at: str
    snapshot_type: str = "rally"
    headline: str = ""
    verdict: str = "UNKNOWN"
    confidence_label: str = "medium"
    summary: str = ""
    metrics: Dict[str, Any] = Field(default_factory=dict)
    tags: List[SessionTagPayload] = Field(default_factory=list)


class SessionTimelineEventPayload(BaseModel):
    event_id: str
    created_at: str
    event_type: str = "analysis"
    title: str
    description: str = ""
    severity: str = "info"
    rally_index: Optional[int] = None
    match_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionIdentityPayload(BaseModel):
    session_id: str
    user_id: str = "local-user"
    label: str = "Untitled Session"
    created_at: str
    updated_at: str
    source: str = "upload"
    match_type: str = "singles"


class SessionStatsPayload(BaseModel):
    rally_count: int = 0
    match_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    unknown_count: int = 0
    average_speed_kmh: float = 0.0
    peak_speed_kmh: float = 0.0
    average_pressure_index: float = 0.0
    average_confidence: float = 0.0
    average_quality: float = 0.0
    export_count: int = 0
    note_count: int = 0
    bookmark_count: int = 0


class SessionProfilePayload(BaseModel):
    tactical_identity: str = "Adaptive"
    momentum_label: str = "neutral"
    training_theme: str = "balanced-foundation"
    readiness_score: float = 0.0
    resilience_score: float = 0.0
    aggression_score: float = 0.0
    recovery_score: float = 0.0
    tags: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    vulnerabilities: List[str] = Field(default_factory=list)


class SessionMemoryPayload(BaseModel):
    top_tactics: List[Dict[str, Any]] = Field(default_factory=list)
    top_focuses: List[Dict[str, Any]] = Field(default_factory=list)
    result_distribution: Dict[str, int] = Field(default_factory=dict)
    trend_cards: List[SessionTrendPayload] = Field(default_factory=list)
    recurring_patterns: List[str] = Field(default_factory=list)
    notable_sequences: List[str] = Field(default_factory=list)


class SessionBundlePayload(BaseModel):
    identity: SessionIdentityPayload
    stats: SessionStatsPayload = Field(default_factory=SessionStatsPayload)
    profile: SessionProfilePayload = Field(default_factory=SessionProfilePayload)
    memory: SessionMemoryPayload = Field(default_factory=SessionMemoryPayload)
    notes: List[SessionNotePayload] = Field(default_factory=list)
    bookmarks: List[SessionBookmarkPayload] = Field(default_factory=list)
    artifacts: List[SessionArtifactPayload] = Field(default_factory=list)
    timeline: List[SessionTimelineEventPayload] = Field(default_factory=list)
    snapshots: List[SessionSnapshotPayload] = Field(default_factory=list)
    focuses: List[SessionFocusPayload] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CacheEntryPayload(BaseModel):
    cache_key: str
    created_at: str
    updated_at: str
    expires_at: Optional[str] = None
    namespace: str = "analysis"
    hit_count: int = 0
    source: str = "computed"
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    payload: Dict[str, Any] = Field(default_factory=dict)


class CacheSummaryPayload(BaseModel):
    total_entries: int = 0
    namespace_distribution: Dict[str, int] = Field(default_factory=dict)
    hottest_keys: List[Dict[str, Any]] = Field(default_factory=list)
    expired_entries: int = 0
    live_entries: int = 0


class ExportSectionPayload(BaseModel):
    title: str
    body: str = ""
    bullets: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExportBundlePayload(BaseModel):
    export_id: str
    created_at: str
    export_type: str = "markdown"
    title: str
    headline: str = ""
    summary: str = ""
    sections: List[ExportSectionPayload] = Field(default_factory=list)
    attachments: List[SessionArtifactPayload] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PromptTemplatePayload(BaseModel):
    template_id: str
    title: str
    category: str = "coach"
    description: str = ""
    system_prompt: str = ""
    user_prompt: str = ""
    tags: List[str] = Field(default_factory=list)
    variables: List[str] = Field(default_factory=list)
    guardrails: List[str] = Field(default_factory=list)
    examples: List[Dict[str, str]] = Field(default_factory=list)


class BlueprintNodePayload(BaseModel):
    node_id: str
    label: str
    description: str = ""
    node_type: str = "phase"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BlueprintEdgePayload(BaseModel):
    source: str
    target: str
    label: str = ""
    weight: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnalysisBlueprintPayload(BaseModel):
    blueprint_id: str
    title: str
    description: str = ""
    category: str = "workflow"
    nodes: List[BlueprintNodePayload] = Field(default_factory=list)
    edges: List[BlueprintEdgePayload] = Field(default_factory=list)
    sections: List[ExportSectionPayload] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionIndexPayload(BaseModel):
    total_sessions: int = 0
    active_session_ids: List[str] = Field(default_factory=list)
    recently_updated: List[str] = Field(default_factory=list)
    labels: Dict[str, str] = Field(default_factory=dict)
    last_synced_at: Optional[str] = None


class SessionSearchResultPayload(BaseModel):
    session_id: str
    label: str
    score: float = 0.0
    matched_fields: List[str] = Field(default_factory=list)
    snippet: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionSearchResponsePayload(BaseModel):
    query: str
    total_hits: int = 0
    results: List[SessionSearchResultPayload] = Field(default_factory=list)


class SessionWriteResultPayload(BaseModel):
    success: bool = True
    session_id: str = ""
    operation: str = "write"
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
