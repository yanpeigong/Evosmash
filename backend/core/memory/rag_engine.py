import os

import chromadb
import numpy as np
from chromadb.utils import embedding_functions

from config import DB_PATH

TACTIC_SEEDS = [
    {
        "id": "T001",
        "name": "Counter Block",
        "content": "When the opponent hits a heavy smash deep into your court, use a soft backhand block to the net and force them forward.",
        "tag": "defense",
        "applicable_events": ["Power Smash", "Smash", "Pressure Rally"],
        "preferred_match_types": ["singles", "doubles"],
        "speed_min": 90,
        "speed_max": 260,
        "court_contexts": ["rear_channel", "rear_wide", "mid_channel"],
        "risk_level": "medium",
    },
    {
        "id": "T002",
        "name": "Deep Lift Reset",
        "content": "On a high serve return, if the opponent stands too far forward, lift quickly to the rear corners and reset the rally.",
        "tag": "attack",
        "applicable_events": ["Pressure Rally", "Drive Exchange", "Control Rally"],
        "preferred_match_types": ["singles", "doubles"],
        "speed_min": 40,
        "speed_max": 180,
        "court_contexts": ["front_central", "mid_central", "front_channel"],
        "risk_level": "low",
    },
    {
        "id": "T003",
        "name": "Cross Drop Finish",
        "content": "When your net spin quality is high, stay forward and be ready to punish the loose cross-court reply.",
        "tag": "net",
        "applicable_events": ["Control Rally", "Pressure Rally"],
        "preferred_match_types": ["singles"],
        "speed_min": 25,
        "speed_max": 120,
        "court_contexts": ["front_central", "front_channel"],
        "risk_level": "medium",
    },
    {
        "id": "T004",
        "name": "Straight Relief Clear",
        "content": "During a pressured backhand transition, play a straight high clear to reduce interception risk.",
        "tag": "defense",
        "applicable_events": ["Pressure Rally", "Drive Exchange", "Smash"],
        "preferred_match_types": ["singles", "doubles"],
        "speed_min": 55,
        "speed_max": 170,
        "court_contexts": ["mid_wide", "rear_wide", "mid_channel"],
        "risk_level": "low",
    },
    {
        "id": "T005",
        "name": "Four Corners Grind",
        "content": "When the opponent starts to slow down physically, stretch them across all four corners to drain the remaining legs.",
        "tag": "tactic",
        "applicable_events": ["Control Rally", "Pressure Rally"],
        "preferred_match_types": ["singles"],
        "speed_min": 20,
        "speed_max": 130,
        "court_contexts": ["mid_central", "rear_central", "mid_channel"],
        "risk_level": "medium",
    },
]

TACTIC_NAME_BY_ID = {seed["id"]: seed["name"] for seed in TACTIC_SEEDS}


class RAGEngine:
    def __init__(self):
        os.makedirs(DB_PATH, exist_ok=True)

        self.client = chromadb.PersistentClient(path=DB_PATH)
        self.emb_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="badminton_tactics_bayesian",
            embedding_function=self.emb_fn,
        )
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
                }
            )
            ids.append(seed["id"])

        self.collection.upsert(documents=documents, metadatas=metadatas, ids=ids)

    def retrieve(self, query_text, context=None, n_results=3):
        results = self.collection.query(query_texts=[query_text], n_results=10)

        if not results["documents"]:
            return []

        candidates = []
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for index, document in enumerate(documents):
            metadata = metadatas[index]
            alpha = max(metadata.get("alpha", 1.0), 0.1)
            beta_val = max(metadata.get("beta", 1.0), 0.1)
            rl_score = np.random.beta(alpha, beta_val)
            semantic_score = 1.0 / (1.0 + distances[index])
            expected_win_rate = (alpha / (alpha + beta_val) * 100) if (alpha + beta_val) else 50.0
            context_score = self._context_score(metadata, context or {})
            quality_weight = self._quality_weight(context or {})
            exploration_bonus = self._exploration_bonus(metadata)
            final_score = quality_weight * (0.3 * semantic_score + 0.35 * rl_score + 0.35 * context_score) + exploration_bonus

            tactic_id = metadata.get("tactic_id")
            tactic_name = metadata.get("name") or TACTIC_NAME_BY_ID.get(tactic_id) or document

            candidates.append(
                {
                    "name": tactic_name,
                    "content": document,
                    "metadata": metadata,
                    "score": final_score,
                    "semantic_score": semantic_score,
                    "bayesian_score": rl_score,
                    "context_score": context_score,
                    "quality_weight": quality_weight,
                    "expected_win_rate": expected_win_rate,
                    "debug_stats": (
                        f"semantic={semantic_score:.2f}/bayes={rl_score:.2f}/context={context_score:.2f}/"
                        f"quality={quality_weight:.2f}/bonus={exploration_bonus:.2f}"
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
        alpha = current_meta.get("alpha", 1.0)
        beta_val = current_meta.get("beta", 1.0)
        matches = current_meta.get("matches", 0)

        context = context or {}
        referee_confidence = float(context.get("referee_confidence", 0.5))
        trajectory_quality = float(context.get("trajectory_quality", 0.5))
        retrieval_confidence = float(context.get("retrieval_confidence", 0.5))

        quality_weight = float(np.clip(0.35 + 0.35 * trajectory_quality + 0.3 * referee_confidence, 0.35, 1.0))
        confidence_weight = float(np.clip(0.45 + 0.55 * retrieval_confidence, 0.45, 1.0))
        exploration_guard = 0.6 if matches < 4 else (0.85 if matches < 10 else 1.0)
        effective_weight = quality_weight * confidence_weight * exploration_guard

        if reward > 0:
            increment = min((reward / 10.0) * effective_weight, 1.0)
            alpha += increment
            delta_target = 'alpha'
        else:
            increment = min((abs(reward) / 5.0) * effective_weight, 1.0)
            beta_val += increment
            delta_target = 'beta'

        if alpha + beta_val > 50:
            alpha *= 0.95
            beta_val *= 0.95

        current_meta["alpha"] = alpha
        current_meta["beta"] = beta_val
        current_meta["matches"] = matches + 1

        self.collection.update(ids=[tactic_id], metadatas=[current_meta])

        adaptation_level = 'strong' if effective_weight >= 0.8 else ('moderate' if effective_weight >= 0.55 else 'conservative')
        policy_update_reason = (
            f"Updated {delta_target} using quality {quality_weight:.2f}, referee confidence {referee_confidence:.2f}, "
            f"retrieval confidence {retrieval_confidence:.2f}, and exploration guard {exploration_guard:.2f}."
        )
        print(f"[RL Evolution] ID:{tactic_id} | alpha:{alpha:.2f} | beta:{beta_val:.2f} | matches:{matches + 1}")

        return {
            'weighted_increment': round(increment, 3),
            'quality_weight': round(quality_weight, 3),
            'confidence_weight': round(confidence_weight, 3),
            'exploration_guard': round(exploration_guard, 3),
            'adaptation_level': adaptation_level,
            'policy_update_reason': policy_update_reason,
            'reward_components': {
                'raw_reward': reward,
                'trajectory_quality': trajectory_quality,
                'referee_confidence': referee_confidence,
                'retrieval_confidence': retrieval_confidence,
            },
        }

    def _context_score(self, metadata, context):
        if not context:
            return 0.5

        score = 0.25
        event_name = context.get('event')
        speed = float(context.get('max_speed_kmh', 0.0))
        match_type = context.get('match_type')
        court_context = context.get('court_context')
        auto_result = context.get('auto_result')

        if event_name and event_name in metadata.get('applicable_events', []):
            score += 0.3
        if match_type and match_type in metadata.get('preferred_match_types', []):
            score += 0.15
        if metadata.get('speed_min', 0) <= speed <= metadata.get('speed_max', 999):
            score += 0.15
        if court_context and court_context in metadata.get('court_contexts', []):
            score += 0.15
        if auto_result == 'LOSS' and metadata.get('tag') in {'defense', 'tactic'}:
            score += 0.08
        if auto_result == 'WIN' and metadata.get('tag') in {'attack', 'net'}:
            score += 0.06

        return float(np.clip(score, 0.0, 1.0))

    def _quality_weight(self, context):
        trajectory_quality = float(context.get('trajectory_quality', 0.5))
        referee_confidence = float(context.get('referee_confidence', 0.5))
        return float(np.clip(0.75 + 0.2 * trajectory_quality + 0.05 * referee_confidence, 0.75, 1.05))

    def _exploration_bonus(self, metadata):
        matches = float(metadata.get('matches', 0))
        if matches < 3:
            return 0.08
        if matches < 6:
            return 0.04
        return 0.0
