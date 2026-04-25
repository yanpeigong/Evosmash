from __future__ import annotations

from typing import Any, Dict, List, Optional

from schemas.session_models import (
    AnalysisBlueprintPayload,
    BlueprintEdgePayload,
    BlueprintNodePayload,
    ExportSectionPayload,
)


class BlueprintService:
    def __init__(self):
        self.blueprints = self._build_blueprints()

    def list_blueprints(self, category: Optional[str] = None) -> List[AnalysisBlueprintPayload]:
        items = list(self.blueprints.values())
        if category:
            items = [item for item in items if item.category == category]
        return items

    def get_blueprint(self, blueprint_id: str) -> Optional[AnalysisBlueprintPayload]:
        return self.blueprints.get(blueprint_id)

    def catalog(self) -> Dict[str, Any]:
        distribution: Dict[str, int] = {}
        for blueprint in self.blueprints.values():
            distribution[blueprint.category] = distribution.get(blueprint.category, 0) + 1
        return {
            "total_blueprints": len(self.blueprints),
            "category_distribution": distribution,
            "ids": sorted(self.blueprints.keys()),
        }

    def to_graph_summary(self, blueprint_id: str) -> Dict[str, Any]:
        blueprint = self.blueprints[blueprint_id]
        return {
            "blueprint_id": blueprint.blueprint_id,
            "title": blueprint.title,
            "node_count": len(blueprint.nodes),
            "edge_count": len(blueprint.edges),
            "tags": blueprint.tags,
            "sections": [section.title for section in blueprint.sections],
        }

    def _build_blueprints(self) -> Dict[str, AnalysisBlueprintPayload]:
        blueprints = [
            self._analysis_workflow_blueprint(),
            self._session_review_blueprint(),
            self._training_conversion_blueprint(),
            self._telemetry_triage_blueprint(),
            self._demo_delivery_blueprint(),
            self._coaching_dialogue_blueprint(),
        ]
        return {blueprint.blueprint_id: blueprint for blueprint in blueprints}

    def _analysis_workflow_blueprint(self) -> AnalysisBlueprintPayload:
        nodes = [
            BlueprintNodePayload(node_id="upload", label="Upload Video", description="Client submits rally or match clip.", node_type="input"),
            BlueprintNodePayload(node_id="court", label="Court Detection", description="Estimate homography and court corners.", node_type="vision"),
            BlueprintNodePayload(node_id="tracking", label="Shuttle Tracking", description="Track the shuttle trajectory across frames.", node_type="vision"),
            BlueprintNodePayload(node_id="pose", label="Pose Analysis", description="Estimate athlete motion quality and readiness.", node_type="vision"),
            BlueprintNodePayload(node_id="physics", label="Physics Analysis", description="Convert trajectory into event and referee state.", node_type="physics"),
            BlueprintNodePayload(node_id="retrieval", label="Tactic Retrieval", description="Retrieve and rerank tactical options.", node_type="memory"),
            BlueprintNodePayload(node_id="coach", label="Coach Response", description="Generate structured advice for the rally.", node_type="agent"),
            BlueprintNodePayload(node_id="report", label="Report Build", description="Assemble diagnostics, summary, and report blocks.", node_type="report"),
        ]
        edges = [
            BlueprintEdgePayload(source="upload", target="court", label="first frame"),
            BlueprintEdgePayload(source="upload", target="tracking", label="video frames"),
            BlueprintEdgePayload(source="tracking", target="pose", label="clip context"),
            BlueprintEdgePayload(source="court", target="physics", label="homography"),
            BlueprintEdgePayload(source="tracking", target="physics", label="trajectory"),
            BlueprintEdgePayload(source="pose", target="physics", label="motion cues"),
            BlueprintEdgePayload(source="physics", target="retrieval", label="state"),
            BlueprintEdgePayload(source="retrieval", target="coach", label="ranked tactics"),
            BlueprintEdgePayload(source="coach", target="report", label="advice"),
            BlueprintEdgePayload(source="physics", target="report", label="diagnostics"),
        ]
        sections = [
            ExportSectionPayload(title="Goal", body="Move from raw clip to explainable rally output."),
            ExportSectionPayload(title="Failure Modes", bullets=["Tracking unavailable", "Pose fallback", "Retrieval empty", "LLM fallback"]),
            ExportSectionPayload(title="Outputs", bullets=["Physics state", "Advice payload", "Tactics", "Diagnostics", "Report"]),
        ]
        return AnalysisBlueprintPayload(
            blueprint_id="workflow.analysis",
            title="Analysis Workflow",
            description="Primary backend pipeline from upload through report output.",
            category="workflow",
            nodes=nodes,
            edges=edges,
            sections=sections,
            tags=["analysis", "pipeline", "core"],
        )

    def _session_review_blueprint(self) -> AnalysisBlueprintPayload:
        nodes = [
            BlueprintNodePayload(node_id="session", label="Session Bundle", node_type="state", description="Persisted user session record."),
            BlueprintNodePayload(node_id="timeline", label="Timeline Events", node_type="history", description="Chronological analysis events."),
            BlueprintNodePayload(node_id="snapshots", label="Snapshots", node_type="history", description="Condensed rally and match snapshots."),
            BlueprintNodePayload(node_id="memory", label="Memory Cards", node_type="summary", description="Recurring patterns and trends."),
            BlueprintNodePayload(node_id="profile", label="Session Profile", node_type="summary", description="Identity, momentum, and readiness."),
            BlueprintNodePayload(node_id="focuses", label="Focus Queue", node_type="training", description="Top training directions from the session."),
            BlueprintNodePayload(node_id="exports", label="Exports", node_type="report", description="Saved markdown and JSON artifacts."),
        ]
        edges = [
            BlueprintEdgePayload(source="session", target="timeline", label="append analyses"),
            BlueprintEdgePayload(source="timeline", target="snapshots", label="condense"),
            BlueprintEdgePayload(source="snapshots", target="memory", label="aggregate"),
            BlueprintEdgePayload(source="memory", target="profile", label="shape identity"),
            BlueprintEdgePayload(source="profile", target="focuses", label="prioritize training"),
            BlueprintEdgePayload(source="session", target="exports", label="render digest"),
        ]
        sections = [
            ExportSectionPayload(title="Purpose", body="Store a coherent history around analyses, notes, and reports."),
            ExportSectionPayload(title="Primary Objects", bullets=["Identity", "Stats", "Profile", "Memory", "Timeline", "Artifacts"]),
            ExportSectionPayload(title="Typical Use", bullets=["Resume past work", "Render dashboards", "Search notable sessions"]),
        ]
        return AnalysisBlueprintPayload(
            blueprint_id="workflow.session-review",
            title="Session Review System",
            description="Shows how stored analysis records become a usable longitudinal session.",
            category="workflow",
            nodes=nodes,
            edges=edges,
            sections=sections,
            tags=["session", "history", "review"],
        )

    def _training_conversion_blueprint(self) -> AnalysisBlueprintPayload:
        nodes = [
            BlueprintNodePayload(node_id="patterns", label="Pattern Signals", node_type="signal", description="Events, results, tempo, pressure."),
            BlueprintNodePayload(node_id="gaps", label="Gap Detection", node_type="analysis", description="Identify recurring vulnerabilities."),
            BlueprintNodePayload(node_id="themes", label="Training Themes", node_type="training", description="Translate gaps into themes."),
            BlueprintNodePayload(node_id="blocks", label="Training Blocks", node_type="training", description="Package themes into drills and blocks."),
            BlueprintNodePayload(node_id="guardrails", label="Guardrails", node_type="training", description="Prevent over-commitment or wrong emphasis."),
            BlueprintNodePayload(node_id="review", label="Review Loop", node_type="feedback", description="Use the next analyses to see whether training worked."),
        ]
        edges = [
            BlueprintEdgePayload(source="patterns", target="gaps", label="interpret"),
            BlueprintEdgePayload(source="gaps", target="themes", label="prioritize"),
            BlueprintEdgePayload(source="themes", target="blocks", label="instantiate"),
            BlueprintEdgePayload(source="themes", target="guardrails", label="boundaries"),
            BlueprintEdgePayload(source="blocks", target="review", label="apply in practice"),
            BlueprintEdgePayload(source="review", target="patterns", label="measure change"),
        ]
        sections = [
            ExportSectionPayload(title="Conversion Logic", body="The system converts repeated rally patterns into focused training work."),
            ExportSectionPayload(title="Key Principle", body="Training themes should reduce uncertainty before they chase complexity."),
            ExportSectionPayload(title="Example Outputs", bullets=["Recovery-first theme", "Forecourt hold timing", "Pressure reset discipline"]),
        ]
        return AnalysisBlueprintPayload(
            blueprint_id="workflow.training-conversion",
            title="Training Conversion Loop",
            description="Maps tactical patterns into practical training outputs and a review loop.",
            category="training",
            nodes=nodes,
            edges=edges,
            sections=sections,
            tags=["training", "feedback", "adaptation"],
        )

    def _telemetry_triage_blueprint(self) -> AnalysisBlueprintPayload:
        nodes = [
            BlueprintNodePayload(node_id="requests", label="Request Logs", node_type="ops"),
            BlueprintNodePayload(node_id="analysis-events", label="Analysis Events", node_type="ops"),
            BlueprintNodePayload(node_id="runtime", label="Runtime Status", node_type="ops"),
            BlueprintNodePayload(node_id="anomalies", label="Anomaly Detection", node_type="ops"),
            BlueprintNodePayload(node_id="triage", label="Triage Notes", node_type="ops"),
            BlueprintNodePayload(node_id="fixes", label="Fix Queue", node_type="ops"),
        ]
        edges = [
            BlueprintEdgePayload(source="requests", target="anomalies", label="latency"),
            BlueprintEdgePayload(source="analysis-events", target="anomalies", label="warning patterns"),
            BlueprintEdgePayload(source="runtime", target="anomalies", label="degraded components"),
            BlueprintEdgePayload(source="anomalies", target="triage", label="summarize"),
            BlueprintEdgePayload(source="triage", target="fixes", label="prioritize"),
        ]
        sections = [
            ExportSectionPayload(title="Primary Goal", body="Convert raw telemetry into action-oriented engineering triage."),
            ExportSectionPayload(title="Signals", bullets=["Request failures", "Latency spikes", "Repeated fallback modes", "Critical component failures"]),
            ExportSectionPayload(title="Outcome", body="A compact fix queue that engineering can act on."),
        ]
        return AnalysisBlueprintPayload(
            blueprint_id="workflow.telemetry-triage",
            title="Telemetry Triage",
            description="Operational blueprint for request and runtime health monitoring.",
            category="ops",
            nodes=nodes,
            edges=edges,
            sections=sections,
            tags=["ops", "telemetry", "triage"],
        )

    def _demo_delivery_blueprint(self) -> AnalysisBlueprintPayload:
        nodes = [
            BlueprintNodePayload(node_id="demo-payloads", label="Demo Payloads", node_type="demo"),
            BlueprintNodePayload(node_id="catalog", label="Demo Catalog", node_type="demo"),
            BlueprintNodePayload(node_id="frontend", label="Frontend Cards", node_type="demo"),
            BlueprintNodePayload(node_id="captions", label="Demo Captions", node_type="demo"),
            BlueprintNodePayload(node_id="telemetry", label="Telemetry Summary", node_type="demo"),
        ]
        edges = [
            BlueprintEdgePayload(source="demo-payloads", target="catalog", label="enumerate"),
            BlueprintEdgePayload(source="demo-payloads", target="frontend", label="render cards"),
            BlueprintEdgePayload(source="demo-payloads", target="captions", label="product copy"),
            BlueprintEdgePayload(source="telemetry", target="frontend", label="ops demo"),
        ]
        sections = [
            ExportSectionPayload(title="Use Case", body="Enable UI and product demos without full model execution."),
            ExportSectionPayload(title="Strength", body="Keeps the frontend unblocked while backend components are still evolving."),
            ExportSectionPayload(title="Guardrail", body="Clearly label synthetic demo payloads so they are not mistaken for live analyses."),
        ]
        return AnalysisBlueprintPayload(
            blueprint_id="workflow.demo-delivery",
            title="Demo Delivery Path",
            description="Explains how synthetic payloads support demos and UI work.",
            category="product",
            nodes=nodes,
            edges=edges,
            sections=sections,
            tags=["demo", "product", "frontend"],
        )

    def _coaching_dialogue_blueprint(self) -> AnalysisBlueprintPayload:
        nodes = [
            BlueprintNodePayload(node_id="state", label="Rally State", node_type="coach"),
            BlueprintNodePayload(node_id="tactics", label="Tactics", node_type="coach"),
            BlueprintNodePayload(node_id="template", label="Prompt Template", node_type="coach"),
            BlueprintNodePayload(node_id="llm", label="LLM Coach", node_type="coach"),
            BlueprintNodePayload(node_id="fallback", label="Fallback Coach", node_type="coach"),
            BlueprintNodePayload(node_id="ui", label="Advice Card", node_type="coach"),
        ]
        edges = [
            BlueprintEdgePayload(source="state", target="template", label="variables"),
            BlueprintEdgePayload(source="tactics", target="template", label="ranked options"),
            BlueprintEdgePayload(source="template", target="llm", label="render prompt"),
            BlueprintEdgePayload(source="template", target="fallback", label="fallback payload"),
            BlueprintEdgePayload(source="llm", target="ui", label="structured advice"),
            BlueprintEdgePayload(source="fallback", target="ui", label="safe advice"),
        ]
        sections = [
            ExportSectionPayload(title="Purpose", body="Explain how structured rally advice is generated."),
            ExportSectionPayload(title="Fallback Logic", bullets=["No API key", "Response parse failure", "Unexpected model output"]),
            ExportSectionPayload(title="UI Contract", bullets=["text", "headline", "focus", "next_step", "confidence_label"]),
        ]
        return AnalysisBlueprintPayload(
            blueprint_id="workflow.coaching-dialogue",
            title="Coaching Dialogue Path",
            description="Covers prompt rendering, model generation, fallback, and UI contract.",
            category="coach",
            nodes=nodes,
            edges=edges,
            sections=sections,
            tags=["coach", "prompt", "ui"],
        )
