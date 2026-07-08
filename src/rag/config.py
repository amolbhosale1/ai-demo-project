"""Settings for the company RAG system (Ollama, Qdrant, GDPR)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Environment-driven configuration for RAG ingestion and querying."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "llama3.2:3b"
    ollama_embedding_model: str = "nomic-embed-text:latest"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "company_info"
    qdrant_vector_size: int = 768
    qdrant_api_key: str | None = None

    # Chunking / retrieval
    rag_top_k: int = 5
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 100
    rag_dataset_dir: Path = Field(default=PROJECT_ROOT / "src" / "rag" / "dataset")

    # GDPR / Privacy
    gdpr_pseudonymize: bool = True
    gdpr_pseudonym_salt: str = "change-me-in-production"
    gdpr_sensitivity: Literal["standard", "high"] = "standard"
    gdpr_exclude_fields: str = ""
    gdpr_retention_days: int = 365
    gdpr_query_log_pii: bool = False
    gdpr_audit_log_path: Path = Field(default=PROJECT_ROOT / "logs" / "rag_audit.jsonl")
    rag_default_role: Literal["employee", "hr_admin", "dpo"] = "employee"

    @field_validator("rag_dataset_dir", "gdpr_audit_log_path", mode="before")
    @classmethod
    def _resolve_path(cls, value: str | Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path

    @property
    def excluded_fields(self) -> set[str]:
        if not self.gdpr_exclude_fields.strip():
            return set()
        return {f.strip().lower() for f in self.gdpr_exclude_fields.split(",") if f.strip()}

    @property
    def ollama_openai_base_url(self) -> str:
        return f"{self.ollama_base_url.rstrip('/')}/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
