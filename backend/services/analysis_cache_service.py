from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

from schemas.session_models import CacheEntryPayload, CacheSummaryPayload


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().isoformat()


class AnalysisCacheService:
    def __init__(self, storage_path: str, default_ttl_minutes: int = 180):
        self.storage_path = storage_path
        self.default_ttl_minutes = default_ttl_minutes
        self._entries: Dict[str, CacheEntryPayload] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.storage_path):
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as file_obj:
                raw = json.load(file_obj)
            self._entries = {
                key: CacheEntryPayload.model_validate(value)
                for key, value in (raw or {}).items()
            }
        except Exception:
            self._entries = {}

    def _persist(self) -> None:
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as file_obj:
            json.dump(
                {key: entry.model_dump() for key, entry in self._entries.items()},
                file_obj,
                ensure_ascii=False,
                indent=2,
            )

    def build_cache_key(self, namespace: str, *parts: Any, payload: Optional[Dict[str, Any]] = None) -> str:
        normalized = {
            "namespace": namespace,
            "parts": [str(part) for part in parts],
            "payload": payload or {},
        }
        digest = hashlib.sha256(
            json.dumps(normalized, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return f"{namespace}:{digest[:24]}"

    def put(
        self,
        cache_key: str,
        payload: Dict[str, Any],
        namespace: str = "analysis",
        ttl_minutes: Optional[int] = None,
        source: str = "computed",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CacheEntryPayload:
        created_at = _iso_now()
        expires_at = None
        ttl_value = ttl_minutes if ttl_minutes is not None else self.default_ttl_minutes
        if ttl_value > 0:
            expires_at = (_utc_now() + timedelta(minutes=ttl_value)).isoformat()

        current = self._entries.get(cache_key)
        hit_count = current.hit_count if current else 0
        entry = CacheEntryPayload(
            cache_key=cache_key,
            created_at=current.created_at if current else created_at,
            updated_at=created_at,
            expires_at=expires_at,
            namespace=namespace,
            hit_count=hit_count,
            source=source,
            tags=tags or [],
            metadata=metadata or {},
            payload=payload,
        )
        self._entries[cache_key] = entry
        self._persist()
        return copy.deepcopy(entry)

    def get(self, cache_key: str, touch: bool = True) -> Optional[CacheEntryPayload]:
        entry = self._entries.get(cache_key)
        if entry is None:
            return None
        if self._is_expired(entry):
            del self._entries[cache_key]
            self._persist()
            return None
        if touch:
            entry.hit_count += 1
            entry.updated_at = _iso_now()
            self._persist()
        return copy.deepcopy(entry)

    def get_payload(self, cache_key: str, touch: bool = True) -> Optional[Dict[str, Any]]:
        entry = self.get(cache_key, touch=touch)
        return copy.deepcopy(entry.payload) if entry else None

    def has(self, cache_key: str) -> bool:
        entry = self._entries.get(cache_key)
        return bool(entry and not self._is_expired(entry))

    def invalidate(self, cache_key: str) -> bool:
        if cache_key not in self._entries:
            return False
        del self._entries[cache_key]
        self._persist()
        return True

    def clear_namespace(self, namespace: str) -> int:
        keys_to_delete = [key for key, value in self._entries.items() if value.namespace == namespace]
        for key in keys_to_delete:
            del self._entries[key]
        if keys_to_delete:
            self._persist()
        return len(keys_to_delete)

    def list_entries(
        self,
        namespace: Optional[str] = None,
        include_expired: bool = False,
        limit: Optional[int] = None,
    ) -> List[CacheEntryPayload]:
        items = []
        for entry in self._entries.values():
            if namespace and entry.namespace != namespace:
                continue
            if not include_expired and self._is_expired(entry):
                continue
            items.append(copy.deepcopy(entry))
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return items[:limit] if limit else items

    def compact(self) -> Dict[str, Any]:
        before = len(self._entries)
        expired_keys = [key for key, value in self._entries.items() if self._is_expired(value)]
        for key in expired_keys:
            del self._entries[key]
        if expired_keys:
            self._persist()
        return {
            "before": before,
            "after": len(self._entries),
            "removed": len(expired_keys),
        }

    def summary(self) -> CacheSummaryPayload:
        namespace_distribution: Dict[str, int] = {}
        hottest = []
        expired_entries = 0
        live_entries = 0

        for entry in self._entries.values():
            namespace_distribution[entry.namespace] = namespace_distribution.get(entry.namespace, 0) + 1
            if self._is_expired(entry):
                expired_entries += 1
            else:
                live_entries += 1

        for entry in sorted(self._entries.values(), key=lambda item: item.hit_count, reverse=True)[:8]:
            hottest.append(
                {
                    "cache_key": entry.cache_key,
                    "namespace": entry.namespace,
                    "hit_count": entry.hit_count,
                    "updated_at": entry.updated_at,
                }
            )

        return CacheSummaryPayload(
            total_entries=len(self._entries),
            namespace_distribution=namespace_distribution,
            hottest_keys=hottest,
            expired_entries=expired_entries,
            live_entries=live_entries,
        )

    def build_rally_signature(
        self,
        match_type: str,
        filename: str = "",
        tracker_diagnostics: Optional[Dict[str, Any]] = None,
        state: Optional[Dict[str, Any]] = None,
    ) -> str:
        tracker_diagnostics = tracker_diagnostics or {}
        state = state or {}
        return self.build_cache_key(
            "rally",
            match_type,
            filename,
            payload={
                "event": state.get("event"),
                "speed": state.get("max_speed_kmh"),
                "quality": state.get("trajectory_quality"),
                "tracker_signal": tracker_diagnostics.get("signal_integrity"),
                "visible_frames": tracker_diagnostics.get("raw_visible_frames"),
            },
        )

    def build_match_signature(
        self,
        match_type: str,
        filename: str = "",
        timeline: Optional[Iterable[Dict[str, Any]]] = None,
    ) -> str:
        timeline = list(timeline or [])
        simplified = []
        for item in timeline[:20]:
            physics = item.get("physics", {}) or {}
            simplified.append(
                {
                    "event": physics.get("event"),
                    "speed": physics.get("max_speed_kmh"),
                    "result": item.get("auto_result"),
                }
            )
        return self.build_cache_key(
            "match",
            match_type,
            filename,
            payload={"timeline": simplified},
        )

    def upsert_demo_payloads(self) -> Dict[str, str]:
        rally_key = self.build_cache_key("demo", "rally")
        match_key = self.build_cache_key("demo", "match")
        self.put(
            rally_key,
            payload={
                "headline": "Demo Rally Cache",
                "kind": "rally",
                "quality": "high",
            },
            namespace="demo",
            ttl_minutes=0,
            tags=["demo", "rally"],
        )
        self.put(
            match_key,
            payload={
                "headline": "Demo Match Cache",
                "kind": "match",
                "quality": "high",
            },
            namespace="demo",
            ttl_minutes=0,
            tags=["demo", "match"],
        )
        return {"rally_cache_key": rally_key, "match_cache_key": match_key}

    def export_state(self) -> Dict[str, Any]:
        return {
            "summary": self.summary().model_dump(),
            "entries": [entry.model_dump() for entry in self.list_entries(include_expired=True)],
        }

    def import_entries(self, entries: Iterable[Dict[str, Any]], replace: bool = False) -> Dict[str, Any]:
        if replace:
            self._entries = {}
        imported = 0
        for item in entries:
            entry = CacheEntryPayload.model_validate(item)
            self._entries[entry.cache_key] = entry
            imported += 1
        self._persist()
        return {
            "imported": imported,
            "total_entries": len(self._entries),
            "replace": replace,
        }

    def touch_many(self, cache_keys: Iterable[str]) -> int:
        touched = 0
        for cache_key in cache_keys:
            entry = self._entries.get(cache_key)
            if entry and not self._is_expired(entry):
                entry.hit_count += 1
                entry.updated_at = _iso_now()
                touched += 1
        if touched:
            self._persist()
        return touched

    def namespace_overview(self, namespace: str) -> Dict[str, Any]:
        entries = self.list_entries(namespace=namespace, include_expired=True)
        live_entries = [entry for entry in entries if not self._is_expired(entry)]
        total_hits = sum(entry.hit_count for entry in entries)
        average_hits = round(total_hits / len(entries), 3) if entries else 0.0
        tags = {}
        for entry in entries:
            for tag in entry.tags:
                tags[tag] = tags.get(tag, 0) + 1
        return {
            "namespace": namespace,
            "total_entries": len(entries),
            "live_entries": len(live_entries),
            "average_hits": average_hits,
            "tag_distribution": tags,
        }

    def _is_expired(self, entry: CacheEntryPayload) -> bool:
        if not entry.expires_at:
            return False
        try:
            return datetime.fromisoformat(entry.expires_at) <= _utc_now()
        except ValueError:
            return False
