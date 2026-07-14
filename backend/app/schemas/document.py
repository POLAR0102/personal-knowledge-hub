from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models.document import DocumentIndexStatus, DocumentStatus
from app.schemas.tag import TagRead


class DocumentRead(BaseModel):
    id: int
    user_id: int
    knowledge_base_id: int
    original_filename: str
    file_type: str
    mime_type: str
    file_size: int
    status: DocumentStatus
    error_message: str | None
    index_status: DocumentIndexStatus
    index_error_message: str | None
    indexed_at: datetime | None
    embedding_model: str | None
    is_favorite: bool
    tags: list[TagRead]
    created_at: datetime
    updated_at: datetime
    chunk_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class DocumentList(BaseModel):
    items: list[DocumentRead]
    total: int
    page: int
    page_size: int


class DocumentStats(BaseModel):
    total: int


class DocumentFavoriteUpdate(BaseModel):
    is_favorite: bool


class DocumentProcessResult(BaseModel):
    document_id: int
    status: DocumentStatus
    chunk_count: int
    updated_at: datetime


class DocumentIndexResult(BaseModel):
    document_id: int
    index_status: DocumentIndexStatus
    chunk_count: int
    vector_count: int
    embedding_model: str
    indexed_at: datetime


class DocumentIndexStatusRead(BaseModel):
    document_id: int
    processing_status: DocumentStatus
    index_status: DocumentIndexStatus
    chunk_count: int
    vector_count: int
    embedding_model: str | None
    indexed_at: datetime | None
    index_error_message: str | None
