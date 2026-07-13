from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.db.models import AgentTaskStatus, AgentTaskType
from app.schemas.rag import RAGCitationRead


AgentTaskInput = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1000),
]


class AgentTaskCreate(BaseModel):
    knowledge_base_id: Annotated[int, Field(gt=0)]
    task_type: AgentTaskType
    task_input: AgentTaskInput


class AgentTaskRead(BaseModel):
    id: int
    user_id: int
    knowledge_base_id: int
    task_type: AgentTaskType
    task_input: str
    status: AgentTaskStatus
    result_content: str | None
    citations: list[RAGCitationRead] = Field(
        default_factory=list,
        validation_alias="citations_json",
    )
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("citations", mode="before")
    @classmethod
    def normalize_null_citations(cls, value: object) -> object:
        return [] if value is None else value


class AgentTaskList(BaseModel):
    items: list[AgentTaskRead]
    total: int
    page: int
    page_size: int
