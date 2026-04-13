from __future__ import annotations

from collections import defaultdict
from typing import Dict, List


class TacticGraph:
    def __init__(self, tactic_seeds: List[Dict]):
        self.tactic_seeds = tactic_seeds
        self.edges = self._build_edges(tactic_seeds)

    def related_profile(self, tactic_id: str | None, context: Dict | None = None) -> Dict:
        if not tactic_id or tactic_id not in self.edges:
            return {
                "graph_bias": 0.0,
                "related_tactics": [],
                "transition_family": "isolated",
            }

        context = context or {}
        links = self.edges[tactic_id]
        scored = []
        for item in links:
            score = item["weight"]
            if context.get("attack_phase") and context.get("attack_phase") == item.get("phase_preference"):
                score += 0.08
            if context.get("event") and context.get("event") in item.get("applicable_events", []):
                score += 0.06
            scored.append({**item, "score": round(score, 3)})

        scored.sort(key=lambda item: item["score"], reverse=True)
        top_related = scored[:3]
        graph_bias = round(min(sum(item["score"] for item in top_related) / 20.0, 0.12), 4)
        transition_family = top_related[0]["style_family"] if top_related else "isolated"
        return {
            "graph_bias": graph_bias,
            "related_tactics": top_related,
            "transition_family": transition_family,
        }

    def _build_edges(self, tactic_seeds: List[Dict]) -> Dict[str, List[Dict]]:
        edges = defaultdict(list)
        for source in tactic_seeds:
            for target in tactic_seeds:
                if source["id"] == target["id"]:
                    continue
                weight = self._relation_weight(source, target)
                if weight <= 0.22:
                    continue
                edges[source["id"]].append(
                    {
                        "tactic_id": target["id"],
                        "name": target["name"],
                        "weight": round(weight, 3),
                        "style_family": target.get("style_family", "balanced"),
                        "phase_preference": target.get("phase_preference", "neutral"),
                        "applicable_events": target.get("applicable_events", []),
                    }
                )
        return dict(edges)

    def _relation_weight(self, source: Dict, target: Dict) -> float:
        weight = 0.0
        if source.get("tag") == target.get("tag"):
            weight += 0.22
        if source.get("style_family") == target.get("style_family"):
            weight += 0.28
        if source.get("phase_preference") == target.get("phase_preference"):
            weight += 0.16
        source_events = set(source.get("applicable_events", []))
        target_events = set(target.get("applicable_events", []))
        if source_events and target_events:
            overlap = len(source_events & target_events) / max(len(source_events | target_events), 1)
            weight += 0.22 * overlap
        source_contexts = set(source.get("court_contexts", []))
        target_contexts = set(target.get("court_contexts", []))
        if source_contexts and target_contexts:
            overlap = len(source_contexts & target_contexts) / max(len(source_contexts | target_contexts), 1)
            weight += 0.12 * overlap
        return weight
