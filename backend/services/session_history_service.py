from __future__ import annotations

import copy
import json
import os
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from schemas.session_models import (
    SessionArtifactPayload,
    SessionBookmarkPayload,
    SessionBundlePayload,
    SessionFocusPayload,
    SessionIdentityPayload,
    SessionIndexPayload,
    SessionMemoryPayload,
    SessionNotePayload,
    SessionProfilePayload,
    SessionSearchResponsePayload,
    SessionSearchResultPayload,
    SessionSnapshotPayload,
    SessionStatsPayload,
    SessionTagPayload,
    SessionTimelineEventPayload,
    SessionTrendPayload,
    SessionWriteResultPayload,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionHistoryService:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.index_path = f"{storage_path}.index.json"
        self._sessions: Dict[str, SessionBundlePayload] = {}
        self._index = SessionIndexPayload()
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as file_obj:
                    raw = json.load(file_obj)
                for session_id, payload in raw.items():
                    self._sessions[session_id] = SessionBundlePayload.model_validate(payload)
            except Exception:
                self._sessions = {}

        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, "r", encoding="utf-8") as file_obj:
                    self._index = SessionIndexPayload.model_validate(json.load(file_obj))
            except Exception:
                self._index = SessionIndexPayload()

        self._rebuild_index()

    def _persist(self) -> None:
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        payload = {session_id: bundle.model_dump() for session_id, bundle in self._sessions.items()}
        with open(self.storage_path, "w", encoding="utf-8") as file_obj:
            json.dump(payload, file_obj, ensure_ascii=False, indent=2)
        with open(self.index_path, "w", encoding="utf-8") as file_obj:
            json.dump(self._index.model_dump(), file_obj, ensure_ascii=False, indent=2)

    def _rebuild_index(self) -> None:
        ordered = sorted(
            self._sessions.values(),
            key=lambda item: item.identity.updated_at,
            reverse=True,
        )
        self._index = SessionIndexPayload(
            total_sessions=len(self._sessions),
            active_session_ids=[item.identity.session_id for item in ordered[:20]],
            recently_updated=[item.identity.session_id for item in ordered[:50]],
            labels={item.identity.session_id: item.identity.label for item in ordered},
            last_synced_at=_utc_now(),
        )

    def create_session(
        self,
        label: str,
        match_type: str = "singles",
        source: str = "upload",
        user_id: str = "local-user",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionBundlePayload:
        session_id = uuid.uuid4().hex
        created_at = _utc_now()
        bundle = SessionBundlePayload(
            identity=SessionIdentityPayload(
                session_id=session_id,
                user_id=user_id,
                label=label,
                created_at=created_at,
                updated_at=created_at,
                source=source,
                match_type=match_type,
            ),
            metadata=metadata or {},
        )
        self._sessions[session_id] = bundle
        self._refresh_bundle(bundle)
        self._persist()
        return self.get_session(session_id)

    def list_sessions(self) -> List[SessionBundlePayload]:
        items = sorted(
            self._sessions.values(),
            key=lambda bundle: bundle.identity.updated_at,
            reverse=True,
        )
        return [copy.deepcopy(item) for item in items]

    def get_session(self, session_id: str) -> Optional[SessionBundlePayload]:
        bundle = self._sessions.get(session_id)
        return copy.deepcopy(bundle) if bundle else None

    def delete_session(self, session_id: str) -> SessionWriteResultPayload:
        if session_id not in self._sessions:
            return SessionWriteResultPayload(
                success=False,
                session_id=session_id,
                operation="delete_session",
                warnings=["Session not found."],
            )
        del self._sessions[session_id]
        self._rebuild_index()
        self._persist()
        return SessionWriteResultPayload(
            success=True,
            session_id=session_id,
            operation="delete_session",
            metadata={"remaining_sessions": len(self._sessions)},
        )

    def rename_session(self, session_id: str, label: str) -> SessionWriteResultPayload:
        bundle = self._sessions.get(session_id)
        if bundle is None:
            return SessionWriteResultPayload(
                success=False,
                session_id=session_id,
                operation="rename_session",
                warnings=["Session not found."],
            )
        bundle.identity.label = label
        bundle.identity.updated_at = _utc_now()
        self._refresh_bundle(bundle)
        self._persist()
        return SessionWriteResultPayload(
            success=True,
            session_id=session_id,
            operation="rename_session",
            metadata={"label": label},
        )

    def append_rally_analysis(self, session_id: str, rally_payload: Dict[str, Any], source: str = "analysis") -> SessionWriteResultPayload:
        bundle = self._sessions.get(session_id)
        if bundle is None:
            return SessionWriteResultPayload(
                success=False,
                session_id=session_id,
                operation="append_rally",
                warnings=["Session not found."],
            )

        timestamp = _utc_now()
        rally_index = bundle.stats.rally_count + 1
        summary = rally_payload.get("summary", {}) or {}
        diagnostics = rally_payload.get("diagnostics", {}) or {}
        physics = rally_payload.get("physics", {}) or {}

        bundle.timeline.append(
            SessionTimelineEventPayload(
                event_id=uuid.uuid4().hex,
                created_at=timestamp,
                event_type="rally-analysis",
                title=summary.get("headline", f"Rally {rally_index} analyzed"),
                description=summary.get("key_takeaway", ""),
                severity="info" if not diagnostics.get("warnings") else "watch",
                rally_index=rally_index,
                match_type=rally_payload.get("match_type"),
                metadata={
                    "source": source,
                    "verdict": rally_payload.get("auto_result", "UNKNOWN"),
                    "event": physics.get("event", "Unknown"),
                    "analysis_quality": diagnostics.get("analysis_quality", "unknown"),
                },
            )
        )

        bundle.snapshots.append(
            SessionSnapshotPayload(
                snapshot_id=uuid.uuid4().hex,
                created_at=timestamp,
                snapshot_type="rally",
                headline=summary.get("headline", f"Rally {rally_index}"),
                verdict=rally_payload.get("auto_result", "UNKNOWN"),
                confidence_label=(summary.get("confidence_label") or "medium"),
                summary=summary.get("key_takeaway", ""),
                metrics={
                    "max_speed_kmh": physics.get("max_speed_kmh", 0.0),
                    "pressure_index": physics.get("pressure_index", 0.0),
                    "trajectory_quality": physics.get("trajectory_quality", 0.0),
                },
                tags=self._build_snapshot_tags(rally_payload),
            )
        )

        bundle.metadata.setdefault("rally_payloads", []).append(rally_payload)
        bundle.identity.updated_at = timestamp
        self._refresh_bundle(bundle)
        self._persist()
        return SessionWriteResultPayload(
            success=True,
            session_id=session_id,
            operation="append_rally",
            metadata={"rally_count": bundle.stats.rally_count},
        )

    def append_match_analysis(self, session_id: str, match_payload: Dict[str, Any], source: str = "analysis") -> SessionWriteResultPayload:
        bundle = self._sessions.get(session_id)
        if bundle is None:
            return SessionWriteResultPayload(
                success=False,
                session_id=session_id,
                operation="append_match",
                warnings=["Session not found."],
            )

        timestamp = _utc_now()
        match_summary = match_payload.get("match_summary", {}) or {}
        metrics = match_summary.get("metrics", {}) or {}
        intelligence = match_summary.get("intelligence", {}) or {}

        bundle.timeline.append(
            SessionTimelineEventPayload(
                event_id=uuid.uuid4().hex,
                created_at=timestamp,
                event_type="match-analysis",
                title=match_summary.get("report", {}).get("headline", "Match analyzed"),
                description=intelligence.get("dominant_pattern", "Match summary recorded."),
                severity="info",
                rally_index=None,
                match_type=bundle.identity.match_type,
                metadata={
                    "source": source,
                    "status": match_payload.get("status", "unknown"),
                    "valid_rallies": match_summary.get("valid_rallies_analyzed", 0),
                    "peak_speed_kmh": metrics.get("peak_speed_kmh", 0.0),
                },
            )
        )

        bundle.snapshots.append(
            SessionSnapshotPayload(
                snapshot_id=uuid.uuid4().hex,
                created_at=timestamp,
                snapshot_type="match",
                headline=match_summary.get("report", {}).get("headline", "Match Report"),
                verdict="SUMMARY",
                confidence_label="medium",
                summary=intelligence.get("dominant_pattern", "Match intelligence recorded."),
                metrics=metrics,
                tags=[
                    SessionTagPayload(label="match", weight=1.0, category="type"),
                    SessionTagPayload(label=intelligence.get("tactical_identity", "Adaptive"), weight=0.8, category="identity"),
                ],
            )
        )

        bundle.metadata.setdefault("match_payloads", []).append(match_payload)
        bundle.identity.updated_at = timestamp
        self._refresh_bundle(bundle)
        self._persist()
        return SessionWriteResultPayload(
            success=True,
            session_id=session_id,
            operation="append_match",
            metadata={"match_count": bundle.stats.match_count},
        )

    def add_note(
        self,
        session_id: str,
        content: str,
        author: str = "coach",
        note_type: str = "summary",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionWriteResultPayload:
        bundle = self._sessions.get(session_id)
        if bundle is None:
            return SessionWriteResultPayload(
                success=False,
                session_id=session_id,
                operation="add_note",
                warnings=["Session not found."],
            )
        bundle.notes.append(
            SessionNotePayload(
                note_id=uuid.uuid4().hex,
                created_at=_utc_now(),
                author=author,
                note_type=note_type,
                content=content,
                metadata=metadata or {},
            )
        )
        bundle.identity.updated_at = _utc_now()
        self._refresh_bundle(bundle)
        self._persist()
        return SessionWriteResultPayload(success=True, session_id=session_id, operation="add_note")

    def add_bookmark(
        self,
        session_id: str,
        title: str,
        rally_index: Optional[int] = None,
        timeline_position: Optional[float] = None,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> SessionWriteResultPayload:
        bundle = self._sessions.get(session_id)
        if bundle is None:
            return SessionWriteResultPayload(
                success=False,
                session_id=session_id,
                operation="add_bookmark",
                warnings=["Session not found."],
            )
        bundle.bookmarks.append(
            SessionBookmarkPayload(
                bookmark_id=uuid.uuid4().hex,
                title=title,
                created_at=_utc_now(),
                rally_index=rally_index,
                timeline_position=timeline_position,
                description=description,
                tags=tags or [],
            )
        )
        bundle.identity.updated_at = _utc_now()
        self._refresh_bundle(bundle)
        self._persist()
        return SessionWriteResultPayload(success=True, session_id=session_id, operation="add_bookmark")

    def add_artifact(
        self,
        session_id: str,
        artifact_type: str,
        title: str,
        path: str = "",
        mime_type: str = "application/json",
        size_bytes: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionWriteResultPayload:
        bundle = self._sessions.get(session_id)
        if bundle is None:
            return SessionWriteResultPayload(
                success=False,
                session_id=session_id,
                operation="add_artifact",
                warnings=["Session not found."],
            )
        bundle.artifacts.append(
            SessionArtifactPayload(
                artifact_id=uuid.uuid4().hex,
                artifact_type=artifact_type,
                title=title,
                created_at=_utc_now(),
                path=path,
                mime_type=mime_type,
                size_bytes=size_bytes,
                metadata=metadata or {},
            )
        )
        bundle.identity.updated_at = _utc_now()
        self._refresh_bundle(bundle)
        self._persist()
        return SessionWriteResultPayload(success=True, session_id=session_id, operation="add_artifact")

    def search_sessions(self, query: str, limit: int = 10) -> SessionSearchResponsePayload:
        normalized_query = (query or "").strip().lower()
        if not normalized_query:
            return SessionSearchResponsePayload(query=query, total_hits=0, results=[])

        results: List[SessionSearchResultPayload] = []
        for bundle in self._sessions.values():
            score, fields, snippet = self._score_session(bundle, normalized_query)
            if score <= 0:
                continue
            results.append(
                SessionSearchResultPayload(
                    session_id=bundle.identity.session_id,
                    label=bundle.identity.label,
                    score=round(score, 3),
                    matched_fields=fields,
                    snippet=snippet,
                    metadata={
                        "updated_at": bundle.identity.updated_at,
                        "match_type": bundle.identity.match_type,
                    },
                )
            )

        results.sort(key=lambda item: item.score, reverse=True)
        return SessionSearchResponsePayload(query=query, total_hits=len(results), results=results[:limit])

    def summary(self) -> Dict[str, Any]:
        sessions = list(self._sessions.values())
        match_type_distribution = Counter(bundle.identity.match_type for bundle in sessions)
        total_notes = sum(len(bundle.notes) for bundle in sessions)
        total_artifacts = sum(len(bundle.artifacts) for bundle in sessions)
        total_bookmarks = sum(len(bundle.bookmarks) for bundle in sessions)
        top_labels = [bundle.identity.label for bundle in sorted(sessions, key=lambda item: item.identity.updated_at, reverse=True)[:5]]
        return {
            "session_count": len(sessions),
            "index": self._index.model_dump(),
            "match_type_distribution": dict(match_type_distribution),
            "total_notes": total_notes,
            "total_artifacts": total_artifacts,
            "total_bookmarks": total_bookmarks,
            "recent_labels": top_labels,
        }

    def export_bundle(self, session_id: str) -> Dict[str, Any]:
        bundle = self._sessions.get(session_id)
        if bundle is None:
            return {"success": False, "session_id": session_id, "reason": "not_found"}
        return {
            "success": True,
            "session_id": session_id,
            "bundle": bundle.model_dump(),
        }

    def clone_session(self, session_id: str, label_suffix: str = "Copy") -> Optional[SessionBundlePayload]:
        bundle = self._sessions.get(session_id)
        if bundle is None:
            return None
        clone = copy.deepcopy(bundle)
        clone.identity.session_id = uuid.uuid4().hex
        clone.identity.label = f"{clone.identity.label} {label_suffix}".strip()
        clone.identity.created_at = _utc_now()
        clone.identity.updated_at = clone.identity.created_at
        self._sessions[clone.identity.session_id] = clone
        self._refresh_bundle(clone)
        self._persist()
        return self.get_session(clone.identity.session_id)

    def hydrate_demo_sessions(self, demo_payloads: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        session_ids = []
        demo_payloads = demo_payloads or []
        for index, payload in enumerate(demo_payloads, start=1):
            bundle = self.create_session(
                label=f"Demo Session {index}",
                match_type=payload.get("match_type", "singles"),
                source="demo",
                metadata={"seeded": True},
            )
            self.append_rally_analysis(bundle.identity.session_id, payload, source="demo")
            session_ids.append(bundle.identity.session_id)
        return session_ids

    def _score_session(self, bundle: SessionBundlePayload, normalized_query: str) -> tuple[float, List[str], str]:
        score = 0.0
        matched_fields: List[str] = []
        snippets: List[str] = []

        candidates = {
            "label": bundle.identity.label,
            "training_theme": bundle.profile.training_theme,
            "identity": bundle.profile.tactical_identity,
            "notes": " ".join(note.content for note in bundle.notes[:8]),
            "patterns": " ".join(bundle.memory.recurring_patterns),
        }

        for field_name, field_text in candidates.items():
            text = (field_text or "").lower()
            if not text:
                continue
            if normalized_query in text:
                score += 2.0 if field_name == "label" else 1.0
                matched_fields.append(field_name)
                snippets.append(field_text[:180])

        if normalized_query in bundle.identity.match_type.lower():
            score += 0.7
            matched_fields.append("match_type")

        for focus in bundle.focuses[:6]:
            if normalized_query in focus.label.lower():
                score += 0.9
                matched_fields.append("focuses")
                snippets.append(focus.rationale or focus.label)

        snippet = " | ".join(snippets[:2])[:240]
        return score, sorted(set(matched_fields)), snippet

    def _refresh_bundle(self, bundle: SessionBundlePayload) -> None:
        bundle.stats = self._build_stats(bundle)
        bundle.memory = self._build_memory(bundle)
        bundle.profile = self._build_profile(bundle)
        bundle.focuses = self._build_focuses(bundle)
        bundle.identity.updated_at = _utc_now()
        self._rebuild_index()

    def _build_stats(self, bundle: SessionBundlePayload) -> SessionStatsPayload:
        rally_payloads = bundle.metadata.get("rally_payloads", []) or []
        match_payloads = bundle.metadata.get("match_payloads", []) or []
        result_distribution = Counter(item.get("auto_result", "UNKNOWN") for item in rally_payloads)
        speeds = [float((item.get("physics", {}) or {}).get("max_speed_kmh", 0.0) or 0.0) for item in rally_payloads]
        pressures = [float((item.get("physics", {}) or {}).get("pressure_index", 0.0) or 0.0) for item in rally_payloads]
        confidences = [
            float((((item.get("diagnostics", {}) or {}).get("confidence_report", {}) or {}).get("calibrated_confidence", 0.0) or 0.0)
            for item in rally_payloads
        ]
        qualities = [
            float(((item.get("physics", {}) or {}).get("trajectory_quality", 0.0) or 0.0))
            for item in rally_payloads
        ]

        def _avg(values: List[float]) -> float:
            return round(sum(values) / len(values), 3) if values else 0.0

        return SessionStatsPayload(
            rally_count=len(rally_payloads),
            match_count=len(match_payloads),
            win_count=result_distribution.get("WIN", 0),
            loss_count=result_distribution.get("LOSS", 0),
            unknown_count=result_distribution.get("UNKNOWN", 0),
            average_speed_kmh=_avg(speeds),
            peak_speed_kmh=round(max(speeds), 3) if speeds else 0.0,
            average_pressure_index=_avg(pressures),
            average_confidence=_avg(confidences),
            average_quality=_avg(qualities),
            export_count=len(bundle.artifacts),
            note_count=len(bundle.notes),
            bookmark_count=len(bundle.bookmarks),
        )

    def _build_memory(self, bundle: SessionBundlePayload) -> SessionMemoryPayload:
        rally_payloads = bundle.metadata.get("rally_payloads", []) or []
        tactics = Counter()
        focuses = Counter()
        patterns = Counter()
        sequences = []
        trends: List[SessionTrendPayload] = []

        for item in rally_payloads:
            top_tactic = (((item.get("tactics", []) or [{}])[0]).get("name", "Neutral reset"))
            tactics[top_tactic] += 1
            focus_label = ((item.get("advice", {}) or {}).get("focus", "Recovery"))
            focuses[focus_label] += 1
            physics = item.get("physics", {}) or {}
            patterns[physics.get("event", "Unknown")] += 1
            sequences.append(
                f"{physics.get('event', 'Unknown')} -> {item.get('auto_result', 'UNKNOWN')} -> {focus_label}"
            )

        confidence_values = [
            float((((item.get("diagnostics", {}) or {}).get("confidence_report", {}) or {}).get("calibrated_confidence", 0.0) or 0.0)
            for item in rally_payloads
        ]
        if confidence_values:
            direction = "up" if confidence_values[-1] >= confidence_values[0] else "down"
            trends.append(
                SessionTrendPayload(
                    label="Confidence",
                    score=round(confidence_values[-1], 3),
                    slope=round(confidence_values[-1] - confidence_values[0], 3),
                    confidence=0.7,
                    direction=direction,
                    evidence=[
                        f"Start {confidence_values[0]:.2f}",
                        f"End {confidence_values[-1]:.2f}",
                    ],
                )
            )

        speed_values = [float((item.get("physics", {}) or {}).get("max_speed_kmh", 0.0) or 0.0) for item in rally_payloads]
        if speed_values:
            direction = "up" if speed_values[-1] >= speed_values[0] else "down"
            trends.append(
                SessionTrendPayload(
                    label="Speed",
                    score=round(speed_values[-1], 3),
                    slope=round(speed_values[-1] - speed_values[0], 3),
                    confidence=0.66,
                    direction=direction,
                    evidence=[
                        f"Start {speed_values[0]:.1f} km/h",
                        f"End {speed_values[-1]:.1f} km/h",
                    ],
                )
            )

        return SessionMemoryPayload(
            top_tactics=[{"name": name, "count": count} for name, count in tactics.most_common(5)],
            top_focuses=[{"label": label, "count": count} for label, count in focuses.most_common(5)],
            result_distribution=dict(Counter(item.get("auto_result", "UNKNOWN") for item in rally_payloads)),
            trend_cards=trends,
            recurring_patterns=[name for name, _ in patterns.most_common(5)],
            notable_sequences=sequences[-8:],
        )

    def _build_profile(self, bundle: SessionBundlePayload) -> SessionProfilePayload:
        stats = bundle.stats
        memory = bundle.memory
        top_focus = ((memory.top_focuses or [{}])[0]).get("label", "Recovery")
        top_pattern = (memory.recurring_patterns or ["Adaptive"])[0]
        readiness_score = round(0.35 * stats.average_confidence + 0.35 * stats.average_quality + 0.3 * min(stats.average_speed_kmh / 180.0, 1.0), 3)
        resilience_score = round(0.55 * (1.0 - min(stats.average_pressure_index, 1.0)) + 0.45 * stats.average_confidence, 3)
        aggression_score = round(min(stats.average_speed_kmh / 170.0, 1.0), 3)
        recovery_score = round(0.5 * stats.average_quality + 0.5 * stats.average_confidence, 3)
        momentum_label = "surging" if stats.win_count > stats.loss_count else "under-pressure" if stats.loss_count > stats.win_count else "neutral"
        strengths = []
        vulnerabilities = []

        if readiness_score >= 0.72:
            strengths.append("Stable readiness across recent analyses")
        if recovery_score >= 0.7:
            strengths.append("Recovery structure is supporting execution")
        if aggression_score >= 0.7:
            strengths.append("Speed ceiling is high enough to pressure opponents")

        if stats.average_pressure_index >= 0.62:
            vulnerabilities.append("Pressure load stays elevated across rallies")
        if stats.average_confidence < 0.5:
            vulnerabilities.append("Decision confidence remains inconsistent")
        if not vulnerabilities:
            vulnerabilities.append("No critical vulnerability cluster is dominant yet")

        return SessionProfilePayload(
            tactical_identity=top_pattern,
            momentum_label=momentum_label,
            training_theme=top_focus.lower().replace(" ", "-"),
            readiness_score=readiness_score,
            resilience_score=resilience_score,
            aggression_score=aggression_score,
            recovery_score=recovery_score,
            tags=[bundle.identity.match_type, momentum_label, top_focus.lower().replace(" ", "-")],
            strengths=strengths,
            vulnerabilities=vulnerabilities,
        )

    def _build_focuses(self, bundle: SessionBundlePayload) -> List[SessionFocusPayload]:
        focuses = []
        memory = bundle.memory
        for item in memory.top_focuses[:3]:
            label = item.get("label", "Recovery")
            count = int(item.get("count", 0) or 0)
            priority = "high" if count >= 3 else "medium"
            focuses.append(
                SessionFocusPayload(
                    label=label,
                    priority=priority,
                    confidence=min(0.45 + count * 0.1, 0.95),
                    rationale=f"{label} appeared as a recurring coaching focus in {count} recent analyses.",
                    drills=[
                        f"Shadow block for {label.lower()} under tempo variation.",
                        f"Constraint feed emphasizing {label.lower()} decisions.",
                    ],
                    guardrails=[
                        "Keep the base organized before increasing commitment.",
                        "Track whether the chosen focus still fits the current rally phase.",
                    ],
                )
            )
        return focuses

    def _build_snapshot_tags(self, rally_payload: Dict[str, Any]) -> List[SessionTagPayload]:
        physics = rally_payload.get("physics", {}) or {}
        advice = rally_payload.get("advice", {}) or {}
        tags = [
            SessionTagPayload(label=physics.get("event", "Unknown"), weight=0.85, category="event"),
            SessionTagPayload(label=advice.get("focus", "Recovery"), weight=0.78, category="focus"),
            SessionTagPayload(label=rally_payload.get("auto_result", "UNKNOWN"), weight=0.92, category="result"),
        ]
        return tags
