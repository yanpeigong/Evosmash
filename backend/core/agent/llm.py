from __future__ import annotations

import json
import re
from typing import Dict, List

from config import LLM_API_KEY, LLM_BASE_URL, LLM_ENABLED, LLM_MODEL_NAME, LLM_TIMEOUT_SECONDS

try:
    import openai
except ImportError:
    openai = None


class CoachAgent:
    def __init__(self):
        self.client = None
        if openai is not None and LLM_ENABLED:
            self.client = openai.OpenAI(
                api_key=LLM_API_KEY,
                base_url=LLM_BASE_URL,
                timeout=LLM_TIMEOUT_SECONDS,
            )

    def is_available(self) -> bool:
        return self.client is not None

    def _format_tactics(self, tactics: List[Dict]) -> str:
        if tactics:
            tactic_lines = []
            for index, tactic in enumerate(tactics, start=1):
                metadata = tactic.get("metadata", {})
                alpha = float(metadata.get("alpha", 1.0) or 1.0)
                beta = float(metadata.get("beta", 1.0) or 1.0)
                win_probability = alpha / (alpha + beta) * 100 if alpha + beta else 50.0
                label = tactic.get("name") or tactic.get("content") or f"Tactic {index}"
                fit_breakdown = tactic.get("fit_breakdown", {})
                tactic_lines.append(
                    f"{index}. {label}\n"
                    f"   Summary: {tactic.get('content', label)}\n"
                    f"   Score: {float(tactic.get('score', 0.0)):.2f} | Expected win rate: {win_probability:.1f}%\n"
                    f"   Context fit: {float(tactic.get('context_score', 0.0)):.2f} | Risk penalty: {float(tactic.get('risk_penalty', 0.0)):.2f}\n"
                    f"   Fit breakdown: {json.dumps(fit_breakdown, ensure_ascii=False)}"
                )
            return "\n".join(tactic_lines)
        return "No tactic recommendations are available."

    def _fallback_payload(self, state: Dict, tactics: List[Dict]) -> Dict:
        top_tactic = tactics[0]["name"] if tactics else state.get("event", "the next pattern")
        next_step = tactics[0].get("recommended_action", "Prepare for the next shot early.") if tactics else "Prepare for the next shot early."
        confidence_label = tactics[0].get("confidence_label", "medium") if tactics else "medium"
        focus = state.get("attack_phase", "Shot selection").replace("_", " ").title()
        return {
            "text": "Stay balanced, recover fast, and prepare for the next contact.",
            "headline": f"Play into {top_tactic}",
            "focus": focus,
            "next_step": next_step,
            "confidence_label": confidence_label,
            "source": "fallback",
        }

    def _extract_json_text(self, content: object) -> str:
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                else:
                    text_parts.append(str(item))
            content = "\n".join(text_parts)

        content = str(content or "").strip()
        fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", content, flags=re.DOTALL)
        if fenced_match:
            return fenced_match.group(1).strip()

        json_match = re.search(r"(\{.*\})", content, flags=re.DOTALL)
        if json_match:
            return json_match.group(1).strip()

        return content

    def _limit_words(self, text: str, max_words: int) -> str:
        words = str(text or "").strip().split()
        if len(words) <= max_words:
            return " ".join(words)
        return " ".join(words[:max_words]).rstrip(" ,.;:") + "."

    def _normalize_payload(self, payload: Dict, state: Dict, tactics: List[Dict]) -> Dict:
        fallback = self._fallback_payload(state, tactics)
        confidence_label = str(payload.get("confidence_label") or fallback["confidence_label"]).strip().lower()
        if confidence_label not in {"high", "medium", "low"}:
            confidence_label = fallback["confidence_label"]

        return {
            "text": self._limit_words(payload.get("text") or fallback["text"], 24),
            "headline": self._limit_words(payload.get("headline") or fallback["headline"], 8),
            "focus": self._limit_words(payload.get("focus") or fallback["focus"], 4),
            "next_step": self._limit_words(payload.get("next_step") or fallback["next_step"], 16),
            "confidence_label": confidence_label,
            "source": payload.get("source") or "llm",
        }

    def _parse_payload(self, content: object, state: Dict, tactics: List[Dict]) -> Dict:
        json_text = self._extract_json_text(content)
        payload = json.loads(json_text)
        if not isinstance(payload, dict):
            raise ValueError("Coach response was not a JSON object.")
        return self._normalize_payload(payload, state, tactics)

    def generate_structured_advice(self, state: Dict, tactics: List[Dict]) -> Dict:
        if not self.is_available():
            return self._fallback_payload(state, tactics)

        tactic_text = self._format_tactics(tactics)

        prompt = f"""
You are a badminton AI coach powered by Bayesian learning.

Current rally state:
- Event: {state['event']} ({state['max_speed_kmh']} km/h)
- Description: {state['description']}
- Attack phase: {state.get('attack_phase', 'neutral')}
- Tempo profile: {state.get('tempo_profile', 'medium')}
- Shot shape: {state.get('shot_shape', 'balanced-rally')}
- Pressure index: {state.get('pressure_index', 0.0)}
- Court context: {state.get('court_context', 'unknown')}

Recommended tactics:
{tactic_text}

Return strict JSON with exactly these keys:
- text
- headline
- focus
- next_step
- confidence_label

Rules:
- Keep `text` under 24 words.
- Keep `headline` under 8 words.
- `focus` should be a short training area such as "Recovery", "Defense", or "Shot selection".
- `next_step` should be one short actionable instruction.
- `confidence_label` must be one of: high, medium, low.
- Prefer the top tactic unless its risk is obviously too high for the current rally phase.
"""

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an assistant that returns only compact JSON objects for badminton rally coaching.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=160,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            payload = self._parse_payload(content, state, tactics)
            payload["source"] = "llm"
            return payload
        except Exception:
            return self._fallback_payload(state, tactics)

    def generate_advice(self, state: Dict, tactics: List[Dict]) -> str:
        return self.generate_structured_advice(state, tactics).get(
            "text",
            "Stay balanced, recover fast, and prepare for the next contact.",
        )
