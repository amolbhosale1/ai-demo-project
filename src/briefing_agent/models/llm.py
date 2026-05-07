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
        if provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY is required for provider=openrouter")
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
            )
        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required for provider=openai")
            self.client = OpenAI(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def summarize(self, client_name: str, items: list[BriefingItem]) -> str:
        if not items:
            return "No approved items available for this period."
        bullet_lines = [
            f"- [{it.source_type}] {it.title}: {it.summary[:180]}"
            for it in items[:20]
        ]
        prompt = (
            f"Create a concise weekly intelligence briefing for {client_name}. "
            "Use the input list and focus on what matters this week.\n\n"
            "Input:\n"
            + "\n".join(bullet_lines)
        )
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
        raise RuntimeError("Unable to generate summary with the configured LLM models.")

