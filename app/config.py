from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str = ""
    llm_model: str = "openai/gpt-oss-120b"
    small_llm_model: str = "openai/gpt-oss-20b"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    docs_collection: str = "docs"
    cache_collection: str = "semantic_cache"

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    top_k: int = 8
    cache_threshold: float = 0.90
    cache_ttl_seconds: int = 7 * 24 * 3600

    database_url: str = "sqlite:///./metrics.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
