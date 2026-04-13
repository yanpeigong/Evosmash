from __future__ import annotations

import os

import chromadb
import numpy as np
from chromadb.utils import embedding_functions

from config import DB_PATH
from .policy_scheduler import PolicyScheduler
from .scenario_memory import ScenarioMemory
from .tactic_catalog import TACTIC_NAME_BY_ID, TACTIC_SEEDS
from .tactic_optimizer import TacticOptimizer


class RAGEngine:
    def __init__(self):
        os.makedirs(DB_PATH, exist_ok=True)

        self.client = chromadb.PersistentClient(path=DB_PATH)
        self.emb_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="badminton_tactics_bayesian",
            embedding_function=self.emb_fn,
        )
        self.optimizer = TacticOptimizer()
        self.scheduler = PolicyScheduler()
        self.scenario_memory = ScenarioMemory(os.path.join(DB_PATH, "scenario_memory.json"))
        self._sync_seed_tactics()

    def _sync_seed_tactics(self):
        print("Syncing Bayesian knowledge base...")

        seed_ids = [seed["id"] for seed in TACTIC_SEEDS]
        existing = self.collection.get(ids=seed_ids)
        existing_metadata = {
            seed_id: metadata
            for seed_id, metadata in zip(existing.get("ids", []), existing.get("metadatas", []))
        }

        documents = []
        metadatas = []
        ids = []
        for seed in TACTIC_SEEDS:
            current_meta = existing_metadata.get(seed["id"], {})
            documents.append(seed["content"])
            metadatas.append(
                {
                    "tactic_id": seed["id"],
                    "tag": seed["tag"],
                    "name": seed["name"],
                    "alpha": current_meta.get("alpha", 1.0),
                    "beta": current_meta.get("beta", 1.0),
                    "matches": current_meta.get("matches", 0),
                    "applicable_events": seed["applicable_events"],
                    "preferred_match_types": seed["preferred_match_types"],
                    "speed_min": seed["speed_min"],
                    "speed_max": seed["speed_max"],
                    "court_contexts": seed["court_contexts"],
                    "risk_level": seed["risk_level"],
                    "style_family": seed.get("style_family", "balanced"),
                    "tempo_band": seed.get("tempo_band", "medium"),
                    "phase_preference": seed.get("phase_preference", "neutral"),
                    "preferred_last_hitter": seed.get("preferred_last_hitter", "UNKNOWN"),
                    "recovery_cost": seed.get("recovery_cost", 0.5),
                    "pressure_gain": seed.get("pressure_gain", 0.5),
                }
            )
            ids.append(seed["id"])

        self.collection.upsert(documents=documents, metadatas=metadatas, ids=ids)

    def retrieve(self, query_text, context=None, n_results=3):
        results = self.collection.query(query_texts=[query_text], n_results=12)

        if not results["documents"]:
            return []

        candidates = []
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        context = context or {}
        scenario_summary = self.scenario_memory.summarize(context)

        for index, document in enumerate(documents):
            metadata = metadatas[index]
            alpha = max(float(metadata.get("alpha", 1.0) or 1.0), 0.1)
            beta_val = max(float(metadata.get("beta", 1.0) or 1.0), 0.1)
            bayes_mean = alpha / (alpha + beta_val)
            thompson_sample = float(np.random.beta(alpha, beta_val))
            bayesian_score = float(np.clip(0.55 * bayes_mean + 0.45 * thompson_sample, 0.0, 1.0))
            semantic_score = float(np.clip(1.0 / (1.0 + distances[index]), 0.0, 1.0))
            optimization = self.optimizer.score_candidate(metadata, semantic_score, bayesian_score, context)
            tactic_id = metadata.get("tactic_id")
            scenario_bias = self.scenario_memory.scenario_bias(context, tactic_id)
            schedule = self.scheduler.schedule_retrieval(context, scenario_summary, metadata)
            scheduler_bias = float(schedule.get("scheduler_bias", 0.0))
            temperature = float(schedule.get("exploration_temperature", 1.0))
            final_score = float(np.clip(optimization["final_score"] * temperature + scenario_bias + scheduler_bias, 0.0, 1.35))
            expected_win_rate = (alpha / (alpha + beta_val) * 100) if (alpha + beta_val) else 50.0
            tactic_name = metadata.get("name") or TACTIC_NAME_BY_ID.get(tactic_id) or document

            candidates.append(
                {
                    "name": tactic_name,
                    "content": document,
                    "metadata": metadata,
                    "score": round(final_score, 3),
                    "semantic_score": round(semantic_score, 3),
                    "bayesian_score": round(bayesian_score, 3),
                    "context_score": optimization["context_score"],
                    "quality_weight": optimization["quality_weight"],
                    "exploration_bonus": optimization["exploration_bonus"],
                    "pressure_bonus": optimization["pressure_bonus"],
                    "risk_penalty": optimization["risk_penalty"],
                    "stability_bonus": optimization["stability_bonus"],
                    "scenario_bias": scenario_bias,
                    "scheduler_profile": schedule,
                    "expected_win_rate": round(expected_win_rate, 2),
                    "fit_breakdown": optimization["fit_breakdown"],
                    "selection_profile": optimization["selection_profile"],
                    "scenario_summary": scenario_summary,
                    "debug_stats": (
                        f"semantic={semantic_score:.2f}/bayes={bayesian_score:.2f}/context={optimization['context_score']:.2f}/"
                        f"quality={optimization['quality_weight']:.2f}/explore={optimization['exploration_bonus']:.2f}/"
                        f"pressure={optimization['pressure_bonus']:.2f}/risk={optimization['risk_penalty']:.2f}/"
                        f"scenario={scenario_bias:.2f}/scheduler={scheduler_bias:.2f}"
                    ),
                }
            )

        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates[:n_results]

    def update_policy(self, tactic_id, reward, context=None):
        result = self.collection.get(ids=[tactic_id])
        if not result["metadatas"]:
            return None

        current_meta = result["metadatas"][0]
        context = context or {}
        scenario_summary = self.scenario_memory.summarize(context)
        schedule = self.scheduler.schedule_update(context, scenario_summary)
        plan = self.optimizer.build_update_plan(current_meta, reward, context)

        learning_scale = float(schedule.get("learning_rate_scale", 1.0))
        if reward >= 0:
            plan["alpha"] = float(plan["alpha"] + plan["weighted_increment"] * max(0.0, learning_scale - 1.0))
        else:
            plan["beta"] = float(plan["beta"] + plan["weighted_increment"] * max(0.0, learning_scale - 1.0))

        current_meta["alpha"] = plan["alpha"]
        current_meta["beta"] = plan["beta"]
        current_meta["matches"] = plan["matches"]

        self.collection.update(ids=[tactic_id], metadatas=[current_meta])
        scenario_summary = self.scenario_memory.update(context, tactic_id, context.get("auto_result", "UNKNOWN"))

        print(
            f"[RL Evolution] ID:{tactic_id} | alpha:{plan['alpha']:.2f} | beta:{plan['beta']:.2f} | matches:{plan['matches']}"
        )

        return {
            "weighted_increment": plan["weighted_increment"],
            "certainty_weight": plan["certainty_weight"],
            "retrieval_weight": plan["retrieval_weight"],
            "contextual_weight": plan["contextual_weight"],
            "adaptation_temperature": plan["adaptation_temperature"],
            "risk_guard": plan["risk_guard"],
            "adaptation_level": plan["adaptation_level"],
            "strategy_tag": plan["strategy_tag"],
            "policy_update_reason": plan["policy_update_reason"],
            "reward_components": plan["reward_components"],
            "scheduler_profile": schedule,
            "scenario_summary": scenario_summary or {},
        }
