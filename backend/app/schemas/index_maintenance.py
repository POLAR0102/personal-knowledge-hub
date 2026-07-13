from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from app.db.models import DocumentIndexStatus


class IndexHealthStatus(str, Enum):
    HEALTHY = "healthy"
    MISSING_VECTORS = "missing_vectors"
    EXTRA_VECTORS = "extra_vectors"
    MODEL_MISMATCH = "model_mismatch"
    NOT_INDEXED = "not_indexed"
    FAILED = "failed"


class DocumentIndexHealthRead(BaseModel):
    document_id: int
    index_status: DocumentIndexStatus
    health_status: IndexHealthStatus
    chunk_count: int
    vector_count: int
    embedding_model: str | None
    current_embedding_model: str
    indexed_at: datetime | None
    index_error_message: str | None


class KnowledgeBaseReindexItem(BaseModel):
    document_id: int
    original_filename: str
    index_status: DocumentIndexStatus
    vector_count: int
    error_message: str | None


class KnowledgeBaseReindexResponse(BaseModel):
    knowledge_base_id: int
    total: int
    succeeded: int
    failed: int
    items: list[KnowledgeBaseReindexItem]
