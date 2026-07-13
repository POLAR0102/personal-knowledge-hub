from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.db.models import NoteSourceType

NoteTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
NoteContent = Annotated[str, Field(min_length=1, max_length=100_000)]


class NoteContentMixin(BaseModel):
    @field_validator("content", check_fields=False)
    @classmethod
    def content_must_not_be_blank(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("content must not be blank")
        return value


class NoteCreate(NoteContentMixin):
    knowledge_base_id: Annotated[int, Field(gt=0)]
    title: NoteTitle
    content: NoteContent


class NoteUpdate(NoteContentMixin):
    title: NoteTitle | None = None
    content: NoteContent | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("title must not be null")
        return value


class NoteRead(BaseModel):
    id: int
    user_id: int
    knowledge_base_id: int
    title: str
    content: str
    source_type: NoteSourceType
    source_agent_task_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NoteList(BaseModel):
    items: list[NoteRead]
    total: int
    page: int
    page_size: int
