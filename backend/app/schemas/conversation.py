from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.db.models import MessageRequestStatus, MessageRole
from app.schemas.rag import RAGCitationRead

ConversationTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
MessageContent = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1000),
]


class ConversationCreate(BaseModel):
    knowledge_base_id: Annotated[int, Field(gt=0)]
    title: ConversationTitle


class MessageCreate(BaseModel):
    content: MessageContent
    top_k: Annotated[int, Field(ge=1, le=10)] = 4
    client_request_id: UUID | None = None


class MessageRead(BaseModel):
    id: int
    conversation_id: int
    role: MessageRole
    content: str
    citations: list[RAGCitationRead] | None = Field(
        validation_alias="citations_json"
    )
    model: str | None
    sequence_number: int
    client_request_id: str | None
    request_status: MessageRequestStatus | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationRead(BaseModel):
    id: int
    user_id: int
    knowledge_base_id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetail(ConversationRead):
    messages: list[MessageRead]


class ConversationList(BaseModel):
    items: list[ConversationRead]
    total: int
    page: int
    page_size: int


class MessagePairResponse(BaseModel):
    user_message: MessageRead
    assistant_message: MessageRead
