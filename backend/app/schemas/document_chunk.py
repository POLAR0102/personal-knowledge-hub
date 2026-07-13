from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentChunkRead(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    content: str
    content_hash: str
    character_count: int
    page_number: int | None
    section_title: str | None
    start_offset: int | None
    end_offset: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentChunkList(BaseModel):
    items: list[DocumentChunkRead]
    total: int
    page: int
    page_size: int
