from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from schemas.session_models import ExportBundlePayload, ExportSectionPayload, SessionArtifactPayload


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExportService:
    def __init__(self, export_dir: str):
        self.export_dir = export_dir
        os.makedirs(export_dir, exist_ok=True)

    def export_rally_markdown(self, rally_payload: Dict[str, Any], title: str = "Rally Analysis") -> ExportBundlePayload:
        physics = rally_payload.get("physics", {}) or {}
        advice = rally_payload.get("advice", {}) or {}
        summary = rally_payload.get("summary", {}) or {}
        diagnostics = rally_payload.get("diagnostics", {}) or {}
        tactics = rally_payload.get("tactics", []) or []

        sections = [
            ExportSectionPayload(
                title="Overview",
                body=summary.get("key_takeaway", "No summary available."),
                bullets=[
                    f"Event: {physics.get('event', 'Unknown')}",
                    f"Result: {rally_payload.get('auto_result', 'UNKNOWN')}",
                    f"Max speed: {physics.get('max_speed_kmh', 0.0)} km/h",
                ],
            ),
            ExportSectionPayload(
                title="Coach Advice",
                body=advice.get("text", ""),
                bullets=[
                    f"Headline: {advice.get('headline', '')}",
                    f"Focus: {advice.get('focus', '')}",
                    f"Next step: {advice.get('next_step', '')}",
                ],
            ),
            ExportSectionPayload(
                title="Diagnostics",
                body="Pipeline and quality snapshot.",
                bullets=[
                    f"Analysis quality: {diagnostics.get('analysis_quality', 'unknown')}",
                    f"Motion feedback: {diagnostics.get('motion_feedback', '')}",
                    f"Warnings: {', '.join(diagnostics.get('warnings', []) or ['none'])}",
                ],
            ),
            ExportSectionPayload(
                title="Tactics",
                body="Top retrieved tactic options.",
                bullets=self._tactic_bullets(tactics),
            ),
        ]
        return self._build_export_bundle(
            export_type="markdown",
            title=title,
            headline=summary.get("headline", "Rally Report"),
            summary=summary.get("key_takeaway", ""),
            sections=sections,
            metadata={"kind": "rally"},
        )

    def export_match_markdown(self, match_payload: Dict[str, Any], title: str = "Match Analysis") -> ExportBundlePayload:
        match_summary = match_payload.get("match_summary", {}) or {}
        metrics = match_summary.get("metrics", {}) or {}
        intelligence = match_summary.get("intelligence", {}) or {}
        report = match_summary.get("report", {}) or {}
        timeline = match_payload.get("timeline", []) or []

        sections = [
            ExportSectionPayload(
                title="Match Summary",
                body=report.get("narrative", "No match narrative available."),
                bullets=[
                    f"Total rallies found: {match_summary.get('total_rallies_found', 0)}",
                    f"Valid rallies analyzed: {match_summary.get('valid_rallies_analyzed', 0)}",
                    f"Peak speed: {metrics.get('peak_speed_kmh', 0.0)} km/h",
                ],
            ),
            ExportSectionPayload(
                title="Intelligence",
                body=intelligence.get("dominant_pattern", "No dominant pattern captured."),
                bullets=[
                    f"Tactical identity: {intelligence.get('tactical_identity', 'Adaptive')}",
                    f"Momentum state: {intelligence.get('momentum_state', 'neutral')}",
                    f"Recommended focus: {', '.join(intelligence.get('recommended_focus', []) or ['none'])}",
                ],
            ),
            ExportSectionPayload(
                title="Metrics",
                body="High-level match metrics.",
                bullets=[
                    f"Average rally duration: {metrics.get('average_rally_duration_sec', 0.0)} sec",
                    f"Average max speed: {metrics.get('average_max_speed_kmh', 0.0)} km/h",
                    f"Average confidence: {metrics.get('average_confidence', 0.0)}",
                ],
            ),
            ExportSectionPayload(
                title="Timeline Highlights",
                body="Recent rally highlights.",
                bullets=self._timeline_bullets(timeline),
            ),
        ]
        return self._build_export_bundle(
            export_type="markdown",
            title=title,
            headline=report.get("headline", "Match Report"),
            summary=report.get("narrative", ""),
            sections=sections,
            metadata={"kind": "match"},
        )

    def export_json(self, payload: Dict[str, Any], title: str, export_type: str = "json") -> ExportBundlePayload:
        sections = [
            ExportSectionPayload(
                title="Raw JSON",
                body=json.dumps(payload, ensure_ascii=False, indent=2),
            )
        ]
        return self._build_export_bundle(
            export_type=export_type,
            title=title,
            headline=title,
            summary="Structured payload export.",
            sections=sections,
            metadata={"kind": "raw-json"},
        )

    def save_bundle(self, bundle: ExportBundlePayload, extension: Optional[str] = None) -> SessionArtifactPayload:
        extension = extension or self._extension_for_bundle(bundle)
        filename = f"{bundle.export_id}.{extension}"
        filepath = os.path.join(self.export_dir, filename)
        content = self.render_bundle(bundle)
        with open(filepath, "w", encoding="utf-8") as file_obj:
            file_obj.write(content)
        size_bytes = os.path.getsize(filepath)
        return SessionArtifactPayload(
            artifact_id=uuid.uuid4().hex,
            artifact_type="export",
            title=bundle.title,
            created_at=_utc_now(),
            path=filepath,
            mime_type=self._mime_type_for_extension(extension),
            size_bytes=size_bytes,
            metadata={
                "export_id": bundle.export_id,
                "export_type": bundle.export_type,
            },
        )

    def render_bundle(self, bundle: ExportBundlePayload) -> str:
        if bundle.export_type in {"json", "structured-json"}:
            return json.dumps(bundle.model_dump(), ensure_ascii=False, indent=2)
        return self.render_markdown(bundle)

    def render_markdown(self, bundle: ExportBundlePayload) -> str:
        lines = [
            f"# {bundle.title}",
            "",
            f"Generated: {bundle.created_at}",
            "",
        ]
        if bundle.headline:
            lines.extend([f"## {bundle.headline}", ""])
        if bundle.summary:
            lines.extend([bundle.summary, ""])
        for section in bundle.sections:
            lines.extend(self._render_markdown_section(section))
        if bundle.attachments:
            lines.extend(["## Attachments", ""])
            for attachment in bundle.attachments:
                lines.append(f"- {attachment.title} ({attachment.path})")
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    def build_session_digest(
        self,
        session_bundle: Dict[str, Any],
        include_notes: bool = True,
        include_artifacts: bool = True,
    ) -> ExportBundlePayload:
        identity = session_bundle.get("identity", {}) or {}
        stats = session_bundle.get("stats", {}) or {}
        profile = session_bundle.get("profile", {}) or {}
        memory = session_bundle.get("memory", {}) or {}
        notes = session_bundle.get("notes", []) or []
        artifacts = session_bundle.get("artifacts", []) or []

        sections = [
            ExportSectionPayload(
                title="Session Identity",
                bullets=[
                    f"Label: {identity.get('label', 'Untitled Session')}",
                    f"Match type: {identity.get('match_type', 'singles')}",
                    f"Updated at: {identity.get('updated_at', '')}",
                ],
            ),
            ExportSectionPayload(
                title="Profile",
                bullets=[
                    f"Tactical identity: {profile.get('tactical_identity', 'Adaptive')}",
                    f"Momentum label: {profile.get('momentum_label', 'neutral')}",
                    f"Training theme: {profile.get('training_theme', 'balanced-foundation')}",
                ],
            ),
            ExportSectionPayload(
                title="Stats",
                bullets=[
                    f"Rallies: {stats.get('rally_count', 0)}",
                    f"Matches: {stats.get('match_count', 0)}",
                    f"Average speed: {stats.get('average_speed_kmh', 0.0)} km/h",
                    f"Peak speed: {stats.get('peak_speed_kmh', 0.0)} km/h",
                ],
            ),
            ExportSectionPayload(
                title="Memory",
                bullets=[
                    f"Top tactics: {', '.join(item.get('name', '') for item in memory.get('top_tactics', [])[:4])}",
                    f"Top focuses: {', '.join(item.get('label', '') for item in memory.get('top_focuses', [])[:4])}",
                    f"Recurring patterns: {', '.join(memory.get('recurring_patterns', [])[:4])}",
                ],
            ),
        ]

        if include_notes:
            sections.append(
                ExportSectionPayload(
                    title="Notes",
                    bullets=[f"{item.get('author', 'system')}: {item.get('content', '')}" for item in notes[:10]],
                )
            )

        if include_artifacts:
            sections.append(
                ExportSectionPayload(
                    title="Artifacts",
                    bullets=[f"{item.get('title', '')} ({item.get('artifact_type', '')})" for item in artifacts[:10]],
                )
            )

        return self._build_export_bundle(
            export_type="markdown",
            title=f"Session Digest - {identity.get('label', 'Untitled Session')}",
            headline=profile.get("tactical_identity", "Adaptive"),
            summary="Condensed session digest for reporting and review.",
            sections=sections,
            metadata={"kind": "session-digest", "session_id": identity.get("session_id")},
        )

    def batch_render(self, bundles: List[ExportBundlePayload]) -> Dict[str, str]:
        return {bundle.export_id: self.render_bundle(bundle) for bundle in bundles}

    def _build_export_bundle(
        self,
        export_type: str,
        title: str,
        headline: str,
        summary: str,
        sections: List[ExportSectionPayload],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExportBundlePayload:
        return ExportBundlePayload(
            export_id=uuid.uuid4().hex,
            created_at=_utc_now(),
            export_type=export_type,
            title=title,
            headline=headline,
            summary=summary,
            sections=sections,
            metadata=metadata or {},
        )

    def _render_markdown_section(self, section: ExportSectionPayload) -> List[str]:
        lines = [f"## {section.title}", ""]
        if section.body:
            lines.extend([section.body, ""])
        for bullet in section.bullets:
            lines.append(f"- {bullet}")
        if section.bullets:
            lines.append("")
        return lines

    def _tactic_bullets(self, tactics: List[Dict[str, Any]]) -> List[str]:
        bullets = []
        for index, tactic in enumerate(tactics[:5], start=1):
            bullets.append(
                f"{index}. {tactic.get('name', 'Unknown')} | "
                f"score {tactic.get('score', 0.0)} | "
                f"expected win rate {tactic.get('expected_win_rate', 0.0)}%"
            )
        return bullets or ["No tactics available."]

    def _timeline_bullets(self, timeline: List[Dict[str, Any]]) -> List[str]:
        bullets = []
        for item in timeline[:6]:
            physics = item.get("physics", {}) or {}
            summary = item.get("summary", {}) or {}
            bullets.append(
                f"Rally {item.get('rally_index', '?')}: "
                f"{physics.get('event', 'Unknown')} | "
                f"{item.get('auto_result', 'UNKNOWN')} | "
                f"{summary.get('headline', 'No headline')}"
            )
        return bullets or ["No timeline items available."]

    def _extension_for_bundle(self, bundle: ExportBundlePayload) -> str:
        if bundle.export_type in {"json", "structured-json"}:
            return "json"
        return "md"

    def _mime_type_for_extension(self, extension: str) -> str:
        mapping = {
            "md": "text/markdown",
            "json": "application/json",
            "txt": "text/plain",
        }
        return mapping.get(extension, "application/octet-stream")
