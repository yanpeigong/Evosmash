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
    },
    {
        "id": "T002",
        "name": "Deep Lift Reset",
        "content": "On a high serve return, if the opponent stands too far forward, lift quickly to the rear corners and reset the rally.",
        "tag": "attack",
    },
    {
        "id": "T003",
        "name": "Cross Drop Finish",
        "content": "When your net spin quality is high, stay forward and be ready to punish the loose cross-court reply.",
        "tag": "net",
    },
    {
        "id": "T004",
        "name": "Straight Relief Clear",
        "content": "During a pressured backhand transition, play a straight high clear to reduce interception risk.",
        "tag": "defense",
    },
    {
        "id": "T005",
        "name": "Four Corners Grind",
        "content": "When the opponent starts to slow down physically, stretch them across all four corners to drain the remaining legs.",
        "tag": "tactic",
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
                }
            )
            ids.append(seed["id"])

        self.collection.upsert(documents=documents, metadatas=metadatas, ids=ids)

    def retrieve(self, query_text, n_results=3):
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
            final_score = 0.4 * semantic_score + 0.6 * rl_score

            tactic_id = metadata.get("tactic_id")
            tactic_name = metadata.get("name") or TACTIC_NAME_BY_ID.get(tactic_id) or document

            candidates.append(
                {
                    "name": tactic_name,
                    "content": document,
                    "metadata": metadata,
                    "score": final_score,
                    "debug_stats": f"alpha={alpha:.1f}/beta={beta_val:.1f}/sample={rl_score:.2f}",
                }
            )

        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates[:n_results]

    def update_policy(self, tactic_id, reward):
        result = self.collection.get(ids=[tactic_id])
        if not result["metadatas"]:
            return

        current_meta = result["metadatas"][0]

        alpha = current_meta.get("alpha", 1.0)
        beta_val = current_meta.get("beta", 1.0)
        matches = current_meta.get("matches", 0)

        if reward > 0:
            alpha += min(reward / 10.0, 1.0)
        else:
            beta_val += min(abs(reward) / 5.0, 1.0)

        if alpha + beta_val > 50:
            alpha *= 0.95
            beta_val *= 0.95

        current_meta["alpha"] = alpha
        current_meta["beta"] = beta_val
        current_meta["matches"] = matches + 1

        self.collection.update(ids=[tactic_id], metadatas=[current_meta])
        print(f"[RL Evolution] ID:{tactic_id} | alpha:{alpha:.2f} | beta:{beta_val:.2f} | matches:{matches + 1}")
