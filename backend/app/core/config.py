from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Personal Knowledge Hub API"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./personal_knowledge_hub.db"
    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    upload_dir: Path = Path("./uploads")
    max_upload_size_mb: int = 20
    embedding_provider: str = "openai-compatible"
    ai_api_key: str | None = None
    ai_base_url: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int | None = None
    embedding_batch_size: int = 32
    embedding_timeout_seconds: float = 30.0
    embedding_max_retries: int = 2
    local_embedding_cache_dir: Path = Path("./model_cache")
    chroma_persist_dir: Path = Path("./chroma_data")
    chroma_collection_name: str = "document_chunks"
    semantic_search_top_k: int = 4
    knowledge_base_reindex_limit: int = 50
    chat_api_key: SecretStr | None = None
    chat_base_url: str | None = "https://api.deepseek.com"
    chat_model: str = "deepseek-v4-flash"
    chat_timeout_seconds: float = 60.0
    chat_max_retries: int = 2
    rag_temperature: float = 0.2
    rag_max_tokens: int = 800
    rag_max_context_chars: int = 12_000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
