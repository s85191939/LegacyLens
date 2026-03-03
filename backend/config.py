"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """LegacyLens configuration."""

    # API Keys
    openai_api_key: str = ""
    openrouter_api_key: str = ""

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""  # Required for Qdrant Cloud
    qdrant_collection: str = "legacylens"

    @field_validator("openai_api_key", "openrouter_api_key", "qdrant_api_key", mode="before")
    @classmethod
    def normalize_api_keys(cls, value):
        """Normalize keys by removing all whitespace/newlines from pasted secrets."""
        if value is None:
            return ""
        if isinstance(value, str):
            return "".join(value.split())
        return value

    @field_validator("qdrant_url", mode="before")
    @classmethod
    def normalize_qdrant_url(cls, value):
        """Trim accidental leading/trailing spaces around URL."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return value

    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    # LLM
    llm_model: str = "gpt-4o"

    # OpenRouter fallback
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-4o-mini"

    # Chunking
    chunk_size: int = 800  # tokens
    chunk_overlap: int = 150  # tokens

    # Retrieval
    top_k: int = 5
    top_k_expanded: int = 8  # for ambiguous queries

    # Codebase
    codebase_path: str = "./codebase/gnucobol"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
