import json

import openai

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME


class CoachAgent:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
        )

    def _format_tactics(self, tactics):
        if tactics:
            tactic_lines = []
            for index, tactic in enumerate(tactics, start=1):
                metadata = tactic["metadata"]
                alpha = metadata.get("alpha", 1.0)
                beta = metadata.get("beta", 1.0)
                win_probability = alpha / (alpha + beta) * 100 if alpha + beta else 50.0
                label = tactic.get("name") or tactic.get("content") or f"Tactic {index}"
                fit_breakdown = tactic.get("fit_breakdown", {})
                tactic_lines.append(
                    f"{index}. {label}\n"
                    f"   Summary: {tactic.get('content', label)}\n"
                    f"   Score: {tactic['score']:.2f} | Expected win rate: {win_probability:.1f}%\n"
                    f"   Context fit: {tactic.get('context_score', 0.0):.2f} | Risk penalty: {tactic.get('risk_penalty', 0.0):.2f}\n"
                    f"   Fit breakdown: {json.dumps(fit_breakdown)}"
                )
            return "\n".join(tactic_lines)
        return "No tactic recommendations are available."

    def _fallback_payload(self, state, tactics):
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

    def generate_structured_advice(self, state, tactics):
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
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=120,
            )
            content = response.choices[0].message.content
            payload = json.loads(content)
            payload["source"] = "llm"
            return payload
        except Exception:
            return self._fallback_payload(state, tactics)

    def generate_advice(self, state, tactics):
        return self.generate_structured_advice(state, tactics).get("text", "Stay balanced, recover fast, and prepare for the next contact.")
