from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

KnowledgeBaseName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
KnowledgeBaseDescription = Annotated[str, Field(max_length=500)]


class KnowledgeBaseCreate(BaseModel):
    name: KnowledgeBaseName
    description: KnowledgeBaseDescription | None = None


class KnowledgeBaseUpdate(BaseModel):
    name: KnowledgeBaseName | None = None
    description: KnowledgeBaseDescription | None = None


class KnowledgeBaseRead(BaseModel):
    id: int
    user_id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeBaseList(BaseModel):
    items: list[KnowledgeBaseRead]
    total: int
    page: int
    page_size: int
