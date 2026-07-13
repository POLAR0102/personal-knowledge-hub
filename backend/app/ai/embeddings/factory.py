from functools import lru_cache

from app.ai.embeddings.base import (
    EmbeddingConfigurationError,
    EmbeddingProvider,
)
from app.ai.embeddings.fastembed_local import FastEmbedEmbeddingProvider
from app.ai.embeddings.openai_compatible import OpenAICompatibleEmbeddingProvider
from app.core.config import Settings, get_settings


def create_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    current_settings = settings or get_settings()
    provider_name = current_settings.embedding_provider.strip().lower()
    if provider_name == "openai-compatible":
        return OpenAICompatibleEmbeddingProvider(
            api_key=current_settings.ai_api_key,
            base_url=current_settings.ai_base_url,
            model=current_settings.embedding_model,
            batch_size=current_settings.embedding_batch_size,
            timeout_seconds=current_settings.embedding_timeout_seconds,
            max_retries=current_settings.embedding_max_retries,
            dimension=current_settings.embedding_dimension,
        )

    if provider_name == "local":
        return FastEmbedEmbeddingProvider(
            model=current_settings.embedding_model,
            batch_size=current_settings.embedding_batch_size,
            dimension=current_settings.embedding_dimension,
            cache_dir=current_settings.local_embedding_cache_dir,
        )

    raise EmbeddingConfigurationError(
        f"Unsupported embedding provider: {current_settings.embedding_provider}"
    )


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return create_embedding_provider()
