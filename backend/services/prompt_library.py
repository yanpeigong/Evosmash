from __future__ import annotations

from typing import Any, Dict, List, Optional

from schemas.session_models import PromptTemplatePayload


class PromptLibrary:
    def __init__(self):
        self.templates = self._build_templates()

    def list_templates(self, category: Optional[str] = None) -> List[PromptTemplatePayload]:
        items = list(self.templates.values())
        if category:
            items = [item for item in items if item.category == category]
        return items

    def get_template(self, template_id: str) -> Optional[PromptTemplatePayload]:
        return self.templates.get(template_id)

    def render(self, template_id: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        template = self.templates[template_id]
        variables = variables or {}
        system_prompt = template.system_prompt
        user_prompt = template.user_prompt
        for key, value in variables.items():
            token = "{" + key + "}"
            system_prompt = system_prompt.replace(token, str(value))
            user_prompt = user_prompt.replace(token, str(value))
        return {
            "template_id": template_id,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        }

    def catalog(self) -> Dict[str, Any]:
        categories: Dict[str, List[str]] = {}
        for template in self.templates.values():
            categories.setdefault(template.category, []).append(template.template_id)
        return {
            "total_templates": len(self.templates),
            "categories": categories,
        }

    def _build_templates(self) -> Dict[str, PromptTemplatePayload]:
        templates = [
            PromptTemplatePayload(
                template_id="coach.rally.micro",
                title="Micro Rally Coach",
                category="coach",
                description="Short tactical cue for a single rally moment.",
                system_prompt=(
                    "You are EvoSmash, a badminton rally coach. "
                    "Keep the answer concise, actionable, and specific to the rally phase."
                ),
                user_prompt=(
                    "Current event: {event}\n"
                    "Attack phase: {attack_phase}\n"
                    "Tempo: {tempo_profile}\n"
                    "Pressure: {pressure_index}\n"
                    "Top tactic: {top_tactic}\n"
                    "Return one compact coaching cue."
                ),
                tags=["coach", "micro", "rally"],
                variables=["event", "attack_phase", "tempo_profile", "pressure_index", "top_tactic"],
                guardrails=[
                    "Avoid generic motivational filler.",
                    "Prefer one action over multiple competing actions.",
                    "Keep the output compact enough for UI cards.",
                ],
                examples=[
                    {
                        "input": "Pressure Rally, under_pressure, fast, 0.68, Front Court Hold",
                        "output": "Recover first, then threaten the forecourt hold only after your base is stable.",
                    }
                ],
            ),
            PromptTemplatePayload(
                template_id="coach.rally.expanded",
                title="Expanded Rally Coach",
                category="coach",
                description="Longer-form rally explanation with rationale and risk.",
                system_prompt=(
                    "You are EvoSmash, a badminton analysis coach. "
                    "Explain the recommendation, why it fits, what the risk is, and what the player should do next."
                ),
                user_prompt=(
                    "Rally summary: {summary}\n"
                    "Event: {event}\n"
                    "Pressure index: {pressure_index}\n"
                    "Top tactic: {top_tactic}\n"
                    "Confidence: {confidence_label}\n"
                    "Produce a clear explanation with sections: What, Why, Risk, Next Step."
                ),
                tags=["coach", "expanded", "education"],
                variables=["summary", "event", "pressure_index", "top_tactic", "confidence_label"],
                guardrails=[
                    "Do not claim certainty beyond the confidence label.",
                    "Tie the explanation back to the rally state.",
                    "Name one next step the athlete can perform immediately.",
                ],
            ),
            PromptTemplatePayload(
                template_id="analyst.match.identity",
                title="Match Tactical Identity",
                category="analyst",
                description="Summarizes a player's tactical identity over a match.",
                system_prompt=(
                    "You are an analyst producing tactical identity summaries for badminton match review."
                ),
                user_prompt=(
                    "Dominant pattern: {dominant_pattern}\n"
                    "Momentum: {momentum_state}\n"
                    "Top focuses: {top_focuses}\n"
                    "Top tactics: {top_tactics}\n"
                    "Return a tactical identity summary in 3 concise paragraphs."
                ),
                tags=["analyst", "match", "identity"],
                variables=["dominant_pattern", "momentum_state", "top_focuses", "top_tactics"],
                guardrails=[
                    "Stay grounded in observable patterns.",
                    "Avoid making unsupported psychological claims.",
                ],
            ),
            PromptTemplatePayload(
                template_id="analyst.timeline.story",
                title="Timeline Storyline",
                category="analyst",
                description="Builds a narrative around rally progression and momentum.",
                system_prompt=(
                    "You are a badminton replay storyteller. "
                    "You turn structured rally summaries into a readable match storyline."
                ),
                user_prompt=(
                    "Timeline: {timeline}\n"
                    "Duel summary: {duel_summary}\n"
                    "Sequence memory: {sequence_memory}\n"
                    "Write a structured storyline with opening, turning point, and closing insight."
                ),
                tags=["storyline", "analyst", "timeline"],
                variables=["timeline", "duel_summary", "sequence_memory"],
                guardrails=[
                    "Do not invent rallies that are not present in the timeline.",
                    "Highlight only a small number of turning points.",
                ],
            ),
            PromptTemplatePayload(
                template_id="trainer.block.plan",
                title="Training Block Planner",
                category="training",
                description="Generates a short training block from recurring focuses.",
                system_prompt=(
                    "You are a badminton training planner. "
                    "Create practical block-based training prescriptions from match review data."
                ),
                user_prompt=(
                    "Primary focus: {primary_focus}\n"
                    "Secondary focus: {secondary_focus}\n"
                    "Pressure trend: {pressure_trend}\n"
                    "Confidence trend: {confidence_trend}\n"
                    "Return 3 training blocks with purpose, duration, and guardrail."
                ),
                tags=["training", "planner"],
                variables=["primary_focus", "secondary_focus", "pressure_trend", "confidence_trend"],
                guardrails=[
                    "Prefer drills that can be explained in one sentence.",
                    "Do not over-prescribe volume for low-confidence states.",
                ],
            ),
            PromptTemplatePayload(
                template_id="trainer.drill.builder",
                title="Drill Builder",
                category="training",
                description="Turns one tactical weakness into a drill progression.",
                system_prompt=(
                    "You are a coach designing progressive badminton drills."
                ),
                user_prompt=(
                    "Weakness: {weakness}\n"
                    "Target state: {target_state}\n"
                    "Available time: {duration_min}\n"
                    "Return warm-up, main drill, pressure variation, and success criteria."
                ),
                tags=["training", "drill"],
                variables=["weakness", "target_state", "duration_min"],
                guardrails=[
                    "Keep the drill progression realistic for one practice session.",
                    "Give a measurable success criterion.",
                ],
            ),
            PromptTemplatePayload(
                template_id="report.executive.summary",
                title="Executive Summary",
                category="report",
                description="High-level summary suitable for dashboards or staff review.",
                system_prompt=(
                    "You summarize badminton analysis for stakeholders who need clarity quickly."
                ),
                user_prompt=(
                    "Session label: {session_label}\n"
                    "Stats: {stats}\n"
                    "Profile: {profile}\n"
                    "Memory: {memory}\n"
                    "Write a concise executive summary with 4 bullet points."
                ),
                tags=["report", "dashboard"],
                variables=["session_label", "stats", "profile", "memory"],
                guardrails=[
                    "Use decision-relevant language.",
                    "Do not repeat raw metrics without interpretation.",
                ],
            ),
            PromptTemplatePayload(
                template_id="report.session.digest",
                title="Session Digest Writer",
                category="report",
                description="Produces a readable digest from a stored session bundle.",
                system_prompt=(
                    "You convert structured badminton session records into a readable digest."
                ),
                user_prompt=(
                    "Identity: {identity}\n"
                    "Stats: {stats}\n"
                    "Profile: {profile}\n"
                    "Notes: {notes}\n"
                    "Create a digest with overview, strengths, risks, and next actions."
                ),
                tags=["report", "session"],
                variables=["identity", "stats", "profile", "notes"],
                guardrails=[
                    "Keep the summary consistent with the bundle.",
                    "If notes disagree with stats, mention the mismatch instead of hiding it.",
                ],
            ),
            PromptTemplatePayload(
                template_id="ops.telemetry.incident",
                title="Telemetry Incident Review",
                category="ops",
                description="Summarizes suspicious request or runtime telemetry.",
                system_prompt=(
                    "You review backend telemetry for engineering triage."
                ),
                user_prompt=(
                    "Telemetry summary: {telemetry_summary}\n"
                    "Recent requests: {recent_requests}\n"
                    "Recent failures: {recent_failures}\n"
                    "Write a short incident review with likely causes and next checks."
                ),
                tags=["ops", "telemetry", "triage"],
                variables=["telemetry_summary", "recent_requests", "recent_failures"],
                guardrails=[
                    "Do not overstate causality.",
                    "Differentiate between hypotheses and confirmed facts.",
                ],
            ),
            PromptTemplatePayload(
                template_id="ops.runtime.health",
                title="Runtime Health Commentary",
                category="ops",
                description="Explains runtime component health for dashboards.",
                system_prompt=(
                    "You explain system health information from a backend runtime matrix."
                ),
                user_prompt=(
                    "Runtime status: {runtime_status}\n"
                    "Components: {components}\n"
                    "Readiness score: {readiness_score}\n"
                    "Explain what is healthy, degraded, and what matters most next."
                ),
                tags=["ops", "runtime", "health"],
                variables=["runtime_status", "components", "readiness_score"],
                guardrails=[
                    "Keep it operationally useful.",
                    "Surface the most important degraded component first.",
                ],
            ),
            PromptTemplatePayload(
                template_id="product.demo.caption",
                title="Demo Caption Generator",
                category="product",
                description="Turns demo payloads into polished caption text.",
                system_prompt=(
                    "You write polished but grounded captions for demo badminton analysis cards."
                ),
                user_prompt=(
                    "Headline: {headline}\n"
                    "Focus: {focus}\n"
                    "Result: {result}\n"
                    "Top tactic: {top_tactic}\n"
                    "Produce a one-paragraph caption suitable for a product demo."
                ),
                tags=["product", "demo", "caption"],
                variables=["headline", "focus", "result", "top_tactic"],
                guardrails=[
                    "Keep the tone informative rather than hype-heavy.",
                    "Do not promise model certainty beyond the provided result.",
                ],
            ),
            PromptTemplatePayload(
                template_id="product.feature.explainer",
                title="Feature Explainer",
                category="product",
                description="Explains one backend feature to non-engineers.",
                system_prompt=(
                    "You explain technical product features in clear, approachable language."
                ),
                user_prompt=(
                    "Feature name: {feature_name}\n"
                    "Purpose: {purpose}\n"
                    "Inputs: {inputs}\n"
                    "Outputs: {outputs}\n"
                    "Explain the feature in 5 short bullet points."
                ),
                tags=["product", "explain"],
                variables=["feature_name", "purpose", "inputs", "outputs"],
                guardrails=[
                    "Use plain language first.",
                    "Name the user-facing value, not just the implementation detail.",
                ],
            ),
        ]
        return {template.template_id: template for template in templates}
