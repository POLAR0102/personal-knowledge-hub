from functools import lru_cache

from app.ai.vector_store.base import VectorStore
from app.ai.vector_store.chroma_store import ChromaVectorStore
from app.core.config import Settings, get_settings


def create_vector_store(settings: Settings | None = None) -> VectorStore:
    current_settings = settings or get_settings()
    return ChromaVectorStore(
        persist_dir=current_settings.chroma_persist_dir,
        collection_name=current_settings.chroma_collection_name,
    )


@lru_cache
def get_vector_store() -> VectorStore:
    return create_vector_store()
