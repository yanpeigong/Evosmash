from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Dict


class ScenarioMemory:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self.state = self._load()

    def summarize(self, context: Dict) -> Dict:
        scenario_key = self._make_key(context)
        bucket = self.state.get(scenario_key, self._empty_bucket())
        total = max(bucket.get("wins", 0) + bucket.get("losses", 0), 1)
        success_rate = bucket.get("wins", 0) / total
        familiarity = min(total / 8.0, 1.0)
        return {
            "scenario_key": scenario_key,
            "encounters": total if total > 1 or (bucket.get("wins", 0) + bucket.get("losses", 0)) > 0 else 0,
            "success_rate": round(success_rate, 3),
            "familiarity": round(familiarity, 3),
            "preferred_tactics": bucket.get("preferred_tactics", {}),
        }

    def update(self, context: Dict, tactic_id: str | None, auto_result: str):
        if not tactic_id:
            return None
        scenario_key = self._make_key(context)
        bucket = self.state.setdefault(scenario_key, self._empty_bucket())
        if auto_result == "WIN":
            bucket["wins"] += 1
        elif auto_result == "LOSS":
            bucket["losses"] += 1
        bucket.setdefault("preferred_tactics", {})
        bucket["preferred_tactics"][tactic_id] = bucket["preferred_tactics"].get(tactic_id, 0) + 1
        self._persist()
        return self.summarize(context)

    def scenario_bias(self, context: Dict, tactic_id: str | None) -> float:
        if not tactic_id:
            return 0.0
        summary = self.summarize(context)
        pref = summary.get("preferred_tactics", {})
        encounters = max(summary.get("encounters", 0), 1)
        tactic_ratio = pref.get(tactic_id, 0) / encounters
        familiarity = summary.get("familiarity", 0.0)
        success_rate = summary.get("success_rate", 0.5)
        return round(0.08 * tactic_ratio * (0.55 + 0.45 * success_rate) * familiarity, 4)

    def _make_key(self, context: Dict) -> str:
        event = context.get("event", "unknown")
        phase = context.get("attack_phase", "neutral")
        court = context.get("court_context", "unknown")
        match_type = context.get("match_type", "singles")
        return f"{match_type}|{event}|{phase}|{court}"

    def _load(self) -> Dict:
        if not os.path.exists(self.storage_path):
            return {}
        try:
            with open(self.storage_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return {}

    def _persist(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as file:
            json.dump(self.state, file, ensure_ascii=False, indent=2)

    def _empty_bucket(self) -> Dict:
        return {
            "wins": 0,
            "losses": 0,
            "preferred_tactics": {},
        }
