"""Application configuration using Pydantic Settings."""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """LegacyLens configuration."""

    # API Keys
    openai_api_key: str = ""

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "legacylens"

    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1536

    # LLM
    llm_model: str = "gpt-4o"

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
