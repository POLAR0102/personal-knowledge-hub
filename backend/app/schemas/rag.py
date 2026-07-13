from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


SearchQuery = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=1000),
]


class SemanticSearchRequest(BaseModel):
    knowledge_base_id: Annotated[int, Field(gt=0)]
    query: SearchQuery
    top_k: Annotated[int | None, Field(ge=1, le=20)] = None


class SemanticSearchResultRead(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    content: str
    chunk_index: int
    page_number: int | None
    section_title: str | None
    distance: float


class SemanticSearchResponse(BaseModel):
    query: str
    knowledge_base_id: int
    results: list[SemanticSearchResultRead]
