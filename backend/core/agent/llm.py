import openai

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL_NAME


class CoachAgent:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
        )

    def generate_advice(self, state, tactics):
        if tactics:
            tactic_lines = []
            for index, tactic in enumerate(tactics, start=1):
                metadata = tactic["metadata"]
                alpha = metadata.get("alpha", 1.0)
                beta = metadata.get("beta", 1.0)
                win_probability = alpha / (alpha + beta) * 100 if alpha + beta else 50.0
                label = tactic.get("name") or tactic.get("content") or f"Tactic {index}"
                tactic_lines.append(
                    f"{index}. {label}\n"
                    f"   Summary: {tactic.get('content', label)}\n"
                    f"   Score: {tactic['score']:.2f} | Expected win rate: {win_probability:.1f}%"
                )
            tactic_text = "\n".join(tactic_lines)
        else:
            tactic_text = "No tactic recommendations are available."

        prompt = f"""
You are a badminton AI coach powered by Bayesian learning.

Current rally state:
- Event: {state['event']} ({state['max_speed_kmh']} km/h)
- Description: {state['description']}

Recommended tactics:
{tactic_text}

Write one short, direct coaching instruction in English.
- Keep it under 24 words.
- If the top tactic is exploratory, sound slightly cautious.
- If confidence is strong, sound decisive.
"""

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=80,
            )
            return response.choices[0].message.content
        except Exception:
            return "Stay balanced, recover fast, and prepare for the next contact."
