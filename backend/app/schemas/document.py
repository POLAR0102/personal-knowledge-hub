from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models.document import DocumentStatus


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


class DocumentProcessResult(BaseModel):
    document_id: int
    status: DocumentStatus
    chunk_count: int
    updated_at: datetime
