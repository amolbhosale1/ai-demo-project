"""Generate embeddings via the Ollama embeddings API."""

from __future__ import annotations

import httpx


class OllamaEmbeddingClient:
    """Thin client around Ollama /api/embeddings."""

    def __init__(self, base_url: str, model: str, timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        with httpx.Client(timeout=self.timeout) as client:
            for text in texts:
                response = client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                response.raise_for_status()
                data = response.json()
                if "embedding" not in data:
                    raise ValueError(f"Embedding not found in Ollama response: {data}")
                embeddings.append(data["embedding"])
        return embeddings
