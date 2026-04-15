from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AdvicePayload(BaseModel):
    text: str
    headline: str = "Stay composed"
    focus: str = "Recovery"
    next_step: str = "Prepare for the next shot."
    confidence_label: str = "medium"
    source: str = "heuristic"


class TacticPayload(BaseModel):
    name: str
    content: str
    score: float = 0.0
    semantic_score: float = 0.0
    bayesian_score: float = 0.0
    context_score: float = 0.0
    quality_weight: float = 1.0
    expected_win_rate: float = 50.0
    confidence_label: str = "medium"
    recommended_action: str = ""
    reason: str = ""
    why_this_tactic: str = ""
    risk_note: str = ""
    exploration_bonus: float = 0.0
    pressure_bonus: float = 0.0
    risk_penalty: float = 0.0
    stability_bonus: float = 0.0
    scenario_bias: float = 0.0
    graph_bias: float = 0.0
    rerank_score: float = 0.0
    continuity_score: float = 0.0
    coverage_score: float = 0.0
    volatility_guard: float = 0.0
    novelty_bonus: float = 0.0
    rank_reason: str = ""
    frontier_hint: str = ""
    scheduler_profile: Dict[str, Any] = Field(default_factory=dict)
    related_tactics: List[Dict[str, Any]] = Field(default_factory=list)
    transition_family: str = "isolated"
    fit_breakdown: Dict[str, Any] = Field(default_factory=dict)
    selection_profile: Dict[str, Any] = Field(default_factory=dict)
    scenario_summary: Dict[str, Any] = Field(default_factory=dict)
    evolution_replay: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    debug_stats: str = ""


class SummaryPayload(BaseModel):
    headline: str
    verdict: str
    confidence_label: str
    key_takeaway: str


class DiagnosticsPayload(BaseModel):
    warnings: List[str] = Field(default_factory=list)
    pipeline: Dict[str, str] = Field(default_factory=dict)
    motion_feedback: str = ""
    trajectory_points: int = 0
    analysis_quality: str = "medium"
    retrieval_summary: Dict[str, Any] = Field(default_factory=dict)
    physics_profile: Dict[str, Any] = Field(default_factory=dict)
    tracker_diagnostics: Dict[str, Any] = Field(default_factory=dict)
    motion_profile: Dict[str, Any] = Field(default_factory=dict)
    rally_quality: Dict[str, Any] = Field(default_factory=dict)
    confidence_report: Dict[str, Any] = Field(default_factory=dict)
    referee_audit: Dict[str, Any] = Field(default_factory=dict)
    sequence_context: Dict[str, Any] = Field(default_factory=dict)
    duel_projection: Dict[str, Any] = Field(default_factory=dict)
    policy_update: Dict[str, Any] = Field(default_factory=dict)


class RallyAnalysisResponse(BaseModel):
    physics: Dict[str, Any]
    advice: AdvicePayload
    tactics: List[TacticPayload] = Field(default_factory=list)
    session_id: Optional[str] = None
    match_type: str
    auto_result: str
    auto_reward: float = 0.0
    summary: SummaryPayload
    diagnostics: DiagnosticsPayload
    report: Dict[str, Any] = Field(default_factory=dict)


class MatchTimelineItem(BaseModel):
    rally_index: int
    duration_sec: float
    physics: Dict[str, Any]
    advice: AdvicePayload
    tactics: List[TacticPayload] = Field(default_factory=list)
    auto_result: str
    auto_reward: float = 0.0
    summary: SummaryPayload
    diagnostics: DiagnosticsPayload
    report: Dict[str, Any] = Field(default_factory=dict)


class MatchAnalysisResponse(BaseModel):
    status: str = "success"
    match_summary: Dict[str, Any]
    timeline: List[MatchTimelineItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
