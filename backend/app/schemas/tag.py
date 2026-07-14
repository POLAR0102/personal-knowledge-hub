from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


TagName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=30),
]


class TagCreate(BaseModel):
    name: TagName


class TagUpdate(BaseModel):
    name: TagName


class TagRead(BaseModel):
    id: int
    user_id: int
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagList(BaseModel):
    items: list[TagRead]
    total: int
    page: int
    page_size: int
