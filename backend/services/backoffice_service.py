from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.utils.insight_timeline import InsightTimelineBuilder
from services.analysis_cache_service import AnalysisCacheService
from services.blueprint_service import BlueprintService
from services.demo_payloads import build_demo_match_payload, build_demo_rally_payload
from services.export_service import ExportService
from services.prompt_library import PromptLibrary
from services.session_history_service import SessionHistoryService
from services.telemetry_service import TelemetryService


class BackofficeService:
    def __init__(
        self,
        session_history: SessionHistoryService,
        cache: AnalysisCacheService,
        exporter: ExportService,
        prompts: PromptLibrary,
        blueprints: BlueprintService,
        telemetry: Optional[TelemetryService] = None,
    ):
        self.session_history = session_history
        self.cache = cache
        self.exporter = exporter
        self.prompts = prompts
        self.blueprints = blueprints
        self.telemetry = telemetry
        self.insight_timeline = InsightTimelineBuilder()

    def dashboard(self) -> Dict[str, Any]:
        session_summary = self.session_history.summary()
        cache_summary = self.cache.summary().model_dump()
        blueprint_catalog = self.blueprints.catalog()
        prompt_catalog = self.prompts.catalog()
        telemetry_summary = self.telemetry.summary() if self.telemetry is not None else {}

        return {
            "headline": "EvoSmash Backoffice Dashboard",
            "session_summary": session_summary,
            "cache_summary": cache_summary,
            "blueprint_catalog": blueprint_catalog,
            "prompt_catalog": prompt_catalog,
            "telemetry_summary": telemetry_summary,
            "recommended_actions": self._recommended_actions(
                session_summary=session_summary,
                cache_summary=cache_summary,
                telemetry_summary=telemetry_summary,
            ),
        }

    def seed_demo_workspace(self, session_count: int = 2) -> Dict[str, Any]:
        demo_session_ids = []
        for index in range(session_count):
            payload = build_demo_rally_payload(match_type="singles" if index % 2 == 0 else "doubles")
            session = self.session_history.create_session(
                label=f"Seeded Demo Workspace {index + 1}",
                match_type=payload.get("match_type", "singles"),
                source="demo-seed",
                metadata={"workspace_seed": True},
            )
            self.session_history.append_rally_analysis(session.identity.session_id, payload, source="demo-seed")
            self.session_history.add_note(
                session.identity.session_id,
                content="This session was seeded to support demo UI and backoffice previews.",
                author="system",
                note_type="seed",
            )
            demo_session_ids.append(session.identity.session_id)

        self.cache.upsert_demo_payloads()
        return {
            "seeded_sessions": demo_session_ids,
            "cache_summary": self.cache.summary().model_dump(),
        }

    def session_workspace(self, session_id: str) -> Dict[str, Any]:
        bundle = self.session_history.get_session(session_id)
        if bundle is None:
            return {"success": False, "session_id": session_id, "reason": "not_found"}

        bundle_dict = bundle.model_dump()
        rally_payloads = bundle_dict.get("metadata", {}).get("rally_payloads", []) or []
        latest_match_payload = ((bundle_dict.get("metadata", {}).get("match_payloads", []) or [None])[-1])
        timeline_view = self.insight_timeline.build(
            timeline=self._mock_timeline_from_rallies(rally_payloads),
            match_type=bundle.identity.match_type,
        )

        exports = {
            "session_digest": self.exporter.build_session_digest(bundle_dict).model_dump(),
            "latest_rally_report": (
                self.exporter.export_rally_markdown(rally_payloads[-1], title="Latest Rally Report").model_dump()
                if rally_payloads else None
            ),
            "latest_match_report": (
                self.exporter.export_match_markdown(latest_match_payload, title="Latest Match Report").model_dump()
                if latest_match_payload else None
            ),
        }

        return {
            "success": True,
            "session": bundle_dict,
            "timeline_view": timeline_view,
            "exports": exports,
            "prompt_suggestions": self.prompt_suggestions(bundle_dict),
            "blueprint_references": self.blueprint_references(),
        }

    def prompt_suggestions(self, session_bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
        profile = session_bundle.get("profile", {}) or {}
        memory = session_bundle.get("memory", {}) or {}
        suggestions = []
        for template in self.prompts.list_templates():
            tags = set(template.tags)
            score = 0.0
            if "coach" in tags and memory.get("top_focuses"):
                score += 1.0
            if "report" in tags and session_bundle.get("notes"):
                score += 0.8
            if "ops" in tags and self.telemetry is not None:
                score += 0.6
            if profile.get("momentum_label") == "under-pressure" and "training" in tags:
                score += 1.1
            if score <= 0:
                continue
            suggestions.append(
                {
                    "template_id": template.template_id,
                    "title": template.title,
                    "category": template.category,
                    "score": round(score, 3),
                    "why": self._prompt_reason(template.template_id, session_bundle),
                }
            )
        suggestions.sort(key=lambda item: item["score"], reverse=True)
        return suggestions[:10]

    def blueprint_references(self) -> List[Dict[str, Any]]:
        return [self.blueprints.to_graph_summary(item.blueprint_id) for item in self.blueprints.list_blueprints()]

    def cache_workspace(self) -> Dict[str, Any]:
        summary = self.cache.summary().model_dump()
        namespace_views = {
            namespace: self.cache.namespace_overview(namespace)
            for namespace in summary.get("namespace_distribution", {}).keys()
        }
        return {
            "summary": summary,
            "namespace_views": namespace_views,
            "entries": [entry.model_dump() for entry in self.cache.list_entries(include_expired=True, limit=50)],
        }

    def export_workspace(self, session_id: str) -> Dict[str, Any]:
        bundle = self.session_history.get_session(session_id)
        if bundle is None:
            return {"success": False, "session_id": session_id, "reason": "not_found"}

        bundle_dict = bundle.model_dump()
        payloads = bundle_dict.get("metadata", {}).get("rally_payloads", []) or []
        match_payloads = bundle_dict.get("metadata", {}).get("match_payloads", []) or []

        export_bundles = [
            self.exporter.build_session_digest(bundle_dict),
            self.exporter.export_json(bundle_dict, title=f"Session JSON - {bundle.identity.label}"),
        ]
        if payloads:
            export_bundles.append(
                self.exporter.export_rally_markdown(payloads[-1], title=f"Latest Rally - {bundle.identity.label}")
            )
        if match_payloads:
            export_bundles.append(
                self.exporter.export_match_markdown(match_payloads[-1], title=f"Latest Match - {bundle.identity.label}")
            )

        rendered = self.exporter.batch_render(export_bundles)
        return {
            "success": True,
            "session_id": session_id,
            "exports": [bundle.model_dump() for bundle in export_bundles],
            "rendered": rendered,
        }

    def ops_workspace(self) -> Dict[str, Any]:
        telemetry_snapshot = self.telemetry.export_snapshot() if self.telemetry is not None else {}
        session_summary = self.session_history.summary()
        cache_summary = self.cache.summary().model_dump()

        return {
            "telemetry": telemetry_snapshot,
            "sessions": session_summary,
            "cache": cache_summary,
            "ops_notes": self._ops_notes(
                telemetry_snapshot=telemetry_snapshot,
                session_summary=session_summary,
                cache_summary=cache_summary,
            ),
        }

    def build_demo_console(self) -> Dict[str, Any]:
        rally_demo = build_demo_rally_payload()
        match_demo = build_demo_match_payload()
        timeline_story = self.insight_timeline.build(match_demo.get("timeline", []), match_type=match_demo.get("timeline", [{}])[0].get("physics", {}).get("match_type", "singles"))
        return {
            "rally_demo": rally_demo,
            "match_demo": match_demo,
            "timeline_story": timeline_story,
            "blueprint_catalog": self.blueprint_references(),
            "prompt_catalog": self.prompts.catalog(),
        }

    def search_everything(self, query: str) -> Dict[str, Any]:
        session_hits = self.session_history.search_sessions(query).model_dump()
        prompt_hits = self._search_prompts(query)
        blueprint_hits = self._search_blueprints(query)
        return {
            "query": query,
            "sessions": session_hits,
            "prompts": prompt_hits,
            "blueprints": blueprint_hits,
        }

    def _search_prompts(self, query: str) -> List[Dict[str, Any]]:
        normalized = (query or "").strip().lower()
        results = []
        for template in self.prompts.list_templates():
            haystack = " ".join(
                [
                    template.template_id,
                    template.title,
                    template.description,
                    " ".join(template.tags),
                ]
            ).lower()
            if normalized and normalized in haystack:
                results.append(
                    {
                        "template_id": template.template_id,
                        "title": template.title,
                        "category": template.category,
                    }
                )
        return results

    def _search_blueprints(self, query: str) -> List[Dict[str, Any]]:
        normalized = (query or "").strip().lower()
        results = []
        for blueprint in self.blueprints.list_blueprints():
            haystack = " ".join(
                [
                    blueprint.blueprint_id,
                    blueprint.title,
                    blueprint.description,
                    " ".join(blueprint.tags),
                ]
            ).lower()
            if normalized and normalized in haystack:
                results.append(
                    {
                        "blueprint_id": blueprint.blueprint_id,
                        "title": blueprint.title,
                        "category": blueprint.category,
                    }
                )
        return results

    def _mock_timeline_from_rallies(self, rally_payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        timeline = []
        for index, payload in enumerate(rally_payloads, start=1):
            timeline.append(
                {
                    "rally_index": index,
                    "duration_sec": round(3.0 + index * 0.4, 2),
                    "physics": payload.get("physics", {}),
                    "advice": payload.get("advice", {}),
                    "tactics": payload.get("tactics", []),
                    "auto_result": payload.get("auto_result", "UNKNOWN"),
                    "summary": payload.get("summary", {}),
                    "diagnostics": payload.get("diagnostics", {}),
                }
            )
        return timeline

    def _recommended_actions(
        self,
        session_summary: Dict[str, Any],
        cache_summary: Dict[str, Any],
        telemetry_summary: Dict[str, Any],
    ) -> List[str]:
        actions = []
        if session_summary.get("session_count", 0) == 0:
            actions.append("Create or seed at least one session so the review workspace has meaningful data.")
        if cache_summary.get("live_entries", 0) == 0:
            actions.append("Prime the analysis cache with demo or recent outputs to speed up repeated views.")
        if telemetry_summary and telemetry_summary.get("analysis_events_stored", 0) == 0:
            actions.append("Trigger a few analysis or demo requests to populate telemetry and ops dashboards.")
        if not actions:
            actions.append("Review session digest exports and refine which views deserve first-class UI support.")
        return actions

    def _prompt_reason(self, template_id: str, session_bundle: Dict[str, Any]) -> str:
        profile = session_bundle.get("profile", {}) or {}
        if template_id.startswith("coach."):
            return f"The session currently emphasizes {profile.get('training_theme', 'balanced-foundation')}."
        if template_id.startswith("training."):
            return "The stored focuses can be translated into a more explicit drill prescription."
        if template_id.startswith("report."):
            return "This session already has enough structure to render a digest or dashboard summary."
        return "This template fits the current workspace context."

    def _ops_notes(
        self,
        telemetry_snapshot: Dict[str, Any],
        session_summary: Dict[str, Any],
        cache_summary: Dict[str, Any],
    ) -> List[str]:
        notes = []
        telemetry_summary = telemetry_snapshot.get("summary", {}) or {}
        if telemetry_summary.get("average_completed_request_ms", 0.0) > 800:
            notes.append("Average request duration is drifting high enough to justify profiling the slower endpoints.")
        if cache_summary.get("expired_entries", 0) > cache_summary.get("live_entries", 0):
            notes.append("Expired cache entries outnumber live ones, so cache compaction would probably help.")
        if session_summary.get("total_notes", 0) == 0:
            notes.append("Sessions currently lack qualitative notes, which may make review exports feel too mechanical.")
        if not notes:
            notes.append("Backoffice signals look balanced enough for the next step to focus on UI integration.")
        return notes
