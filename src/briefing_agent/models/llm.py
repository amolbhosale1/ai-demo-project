from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI

from briefing_agent.types import BriefingItem


def _load_env_file() -> None:
    """Load environment variables from project root .env if present."""
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


class LLMClient:
    def __init__(self, provider: str, model: str, fallback_models: list[str] | None = None):
        _load_env_file()
        self.provider = provider
        self.model = model
        self.fallback_models = fallback_models or []
        self.client: OpenAI | None = None
        if provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if api_key:
                self.client = OpenAI(
                    api_key=api_key,
                    base_url="https://openrouter.ai/api/v1",
                )
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.client = OpenAI(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def summarize(self, client_name: str, items: list[BriefingItem]) -> str:
        if not items:
            return "No approved items available for this period."
        prompt = self._build_structured_prompt(client_name, items)
        if self.client is None:
            return self._fallback_summary(client_name, items)
        models_to_try = [self.model, *self.fallback_models]
        for model_name in models_to_try:
            try:
                completion = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You write crisp executive briefings."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                )
                return completion.choices[0].message.content or ""
            except Exception:
                continue
        return self._fallback_summary(client_name, items)

    def _fallback_summary(self, client_name: str, items: list[BriefingItem]) -> str:
        articles = [i for i in items if i.category == "article"][:8]
        data_points = [i for i in items if i.category == "data_point"][:6]
        top_titles = [a.title for a in articles[:3]]
        top_news = "\n".join([f"- {title}" for title in top_titles]) if top_titles else "- No major headlines identified"
        major_developments = "\n".join(
            [f"- {a.title}: {(a.summary or '').strip()[:160]}" for a in articles]
        ) or "- No article developments available."
        economic_snapshot = "\n".join([f"- {d.summary}" for d in data_points]) or "- No economic data points available."
        implications = "\n".join(
            [
                "- Public affairs and reputation risk remains elevated due to policy and regulatory volatility.",
                "- Cross-border political and market developments may affect stakeholder messaging cadence.",
                "- Use selective media engagement based on issues with clear client relevance and timing.",
            ]
        )
        return (
            f"HEADLINE: Weekly Intelligence Brief - {client_name}\n"
            f"SUBHEADING: Key developments across media, policy, markets, and reputation landscape this week.\n\n"
            f"MAIN NEWS:\n{top_news}\n\n"
            f"MAJOR DEVELOPMENTS:\n{major_developments}\n\n"
            f"ECONOMIC SNAPSHOT:\n{economic_snapshot}\n\n"
            f"IMPLICATIONS FOR CLIENTS:\n{implications}\n\n"
            "NOTES:\n- AI model summary unavailable; structured fallback summary used."
        )

    def _build_structured_prompt(self, client_name: str, items: list[BriefingItem]) -> str:
        bullet_lines = [f"- [{it.source_type}] {it.title}: {it.summary[:220]}" for it in items[:25]]
        return (
            f"Create a comprehensive weekly intelligence briefing for {client_name}.\n"
            "Use exactly this output format with section labels and bullet points:\n"
            "HEADLINE: <single line>\n"
            "SUBHEADING: <single line>\n\n"
            "MAIN NEWS:\n"
            "- <top headline 1>\n"
            "- <top headline 2>\n"
            "- <top headline 3>\n\n"
            "MAJOR DEVELOPMENTS:\n"
            "- <development + why it matters>\n"
            "- <development + why it matters>\n\n"
            "ECONOMIC SNAPSHOT:\n"
            "- <data point and interpretation>\n\n"
            "IMPLICATIONS FOR CLIENTS:\n"
            "- <actionable implication>\n"
            "- <actionable implication>\n\n"
            "Keep it executive-friendly, specific, and not generic.\n\n"
            "Input items:\n"
            + "\n".join(bullet_lines)
        )

