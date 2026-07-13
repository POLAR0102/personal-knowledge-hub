from collections.abc import Generator
from pathlib import Path

import chromadb
import pytest

from app.ai.vector_store.base import (
    VectorRecord,
    VectorStoreConfigurationError,
    VectorStoreInputError,
)
from app.ai.vector_store.chroma_store import ChromaVectorStore


@pytest.fixture
def vector_store(tmp_path: Path) -> Generator[ChromaVectorStore, None, None]:
    store = ChromaVectorStore(tmp_path / "chroma", "test_document_chunks")
    try:
        yield store
    finally:
        store.close()


def make_record(
    chunk_id: int,
    *,
    user_id: int = 1,
    knowledge_base_id: int = 1,
    document_id: int = 1,
    chunk_index: int = 0,
    content: str | None = None,
    embedding: list[float] | None = None,
    page_number: int | None = None,
    section_title: str | None = None,
    embedding_model: str = "test-embedding-model",
) -> VectorRecord:
    return VectorRecord(
        chunk_id=chunk_id,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        document_id=document_id,
        chunk_index=chunk_index,
        filename=f"document-{document_id}.txt",
        content=content or f"content {chunk_id}",
        content_hash=f"hash-{chunk_id}",
        embedding_model=embedding_model,
        embedding=embedding or [1.0, 0.0],
        page_number=page_number,
        section_title=section_title,
    )


def test_collection_is_created_with_cosine_distance(
    vector_store: ChromaVectorStore,
) -> None:
    assert vector_store.collection_health().healthy is True
    assert vector_store.collection_health().record_count == 0


def test_existing_non_cosine_collection_is_rejected(tmp_path: Path) -> None:
    persist_dir = tmp_path / "chroma"
    client = chromadb.PersistentClient(path=persist_dir)
    client.get_or_create_collection(
        name="test_document_chunks",
        embedding_function=None,
    )
    client.close()

    with pytest.raises(VectorStoreConfigurationError, match="cosine"):
        ChromaVectorStore(persist_dir, "test_document_chunks")


def test_upsert_single_chunk(vector_store: ChromaVectorStore) -> None:
    vector_store.upsert_chunks([make_record(1)])

    assert vector_store.count_by_document(document_id=1, user_id=1) == 1


def test_upsert_multiple_chunks(vector_store: ChromaVectorStore) -> None:
    vector_store.upsert_chunks(
        [
            make_record(1, chunk_index=0),
            make_record(2, chunk_index=1),
            make_record(3, chunk_index=2),
        ]
    )

    assert vector_store.count_by_document(document_id=1, user_id=1) == 3


def test_repeated_upsert_replaces_existing_id(
    vector_store: ChromaVectorStore,
) -> None:
    vector_store.upsert_chunks([make_record(1, content="old content")])
    vector_store.upsert_chunks([make_record(1, content="new content")])

    results = vector_store.search([1.0, 0.0], user_id=1, knowledge_base_id=1, top_k=4)
    assert vector_store.count_by_document(document_id=1, user_id=1) == 1
    assert results[0].content == "new content"


def test_search_maps_metadata_and_relevance_order(
    vector_store: ChromaVectorStore,
) -> None:
    vector_store.upsert_chunks(
        [
            make_record(
                1,
                chunk_index=0,
                embedding=[1.0, 0.0],
                page_number=3,
                section_title="Introduction",
            ),
            make_record(
                2,
                chunk_index=1,
                embedding=[0.0, 1.0],
            ),
        ]
    )

    results = vector_store.search([1.0, 0.0], user_id=1, knowledge_base_id=1, top_k=2)

    assert [result.chunk_id for result in results] == [1, 2]
    assert results[0].filename == "document-1.txt"
    assert results[0].page_number == 3
    assert results[0].section_title == "Introduction"
    assert results[0].distance == pytest.approx(0.0)
    assert results[1].page_number is None
    assert results[1].section_title is None
    assert results[0].distance < results[1].distance


def test_search_isolates_users(vector_store: ChromaVectorStore) -> None:
    vector_store.upsert_chunks(
        [
            make_record(1, user_id=1, content="user one"),
            make_record(2, user_id=2, document_id=2, content="user two"),
        ]
    )

    results = vector_store.search([1.0, 0.0], user_id=1, knowledge_base_id=1, top_k=4)

    assert [result.content for result in results] == ["user one"]


def test_search_isolates_knowledge_bases(
    vector_store: ChromaVectorStore,
) -> None:
    vector_store.upsert_chunks(
        [
            make_record(1, knowledge_base_id=1, content="knowledge base one"),
            make_record(
                2,
                knowledge_base_id=2,
                document_id=2,
                content="knowledge base two",
            ),
        ]
    )

    results = vector_store.search([1.0, 0.0], user_id=1, knowledge_base_id=2, top_k=4)

    assert [result.content for result in results] == ["knowledge base two"]


def test_search_can_isolate_embedding_models(
    vector_store: ChromaVectorStore,
) -> None:
    vector_store.upsert_chunks(
        [
            make_record(1, content="current model"),
            make_record(
                2,
                document_id=2,
                content="old model",
                embedding_model="old-embedding-model",
            ),
        ]
    )

    results = vector_store.search(
        [1.0, 0.0],
        user_id=1,
        knowledge_base_id=1,
        top_k=4,
        embedding_model="test-embedding-model",
    )

    assert [result.content for result in results] == ["current model"]


def test_delete_by_document_is_scoped_to_user(
    vector_store: ChromaVectorStore,
) -> None:
    vector_store.upsert_chunks(
        [
            make_record(1, user_id=1, document_id=1),
            make_record(2, user_id=1, document_id=2),
            make_record(3, user_id=2, document_id=1),
        ]
    )

    vector_store.delete_by_document(document_id=1, user_id=1)

    assert vector_store.count_by_document(document_id=1, user_id=1) == 0
    assert vector_store.count_by_document(document_id=2, user_id=1) == 1
    assert vector_store.count_by_document(document_id=1, user_id=2) == 1


def test_delete_by_knowledge_base_is_scoped_to_user(
    vector_store: ChromaVectorStore,
) -> None:
    vector_store.upsert_chunks(
        [
            make_record(1, user_id=1, knowledge_base_id=1, document_id=1),
            make_record(2, user_id=1, knowledge_base_id=2, document_id=2),
            make_record(3, user_id=2, knowledge_base_id=1, document_id=3),
        ]
    )

    vector_store.delete_by_knowledge_base(knowledge_base_id=1, user_id=1)

    results_user_one = vector_store.search(
        [1.0, 0.0],
        user_id=1,
        knowledge_base_id=1,
        top_k=4,
    )
    results_user_two = vector_store.search(
        [1.0, 0.0],
        user_id=2,
        knowledge_base_id=1,
        top_k=4,
    )
    assert results_user_one == []
    assert [result.chunk_id for result in results_user_two] == [3]
    assert vector_store.count_by_document(document_id=2, user_id=1) == 1


@pytest.mark.parametrize("top_k", [0, 21])
def test_top_k_must_be_between_one_and_twenty(
    vector_store: ChromaVectorStore,
    top_k: int,
) -> None:
    with pytest.raises(VectorStoreInputError, match="top_k"):
        vector_store.search([1.0, 0.0], user_id=1, knowledge_base_id=1, top_k=top_k)


def test_vectors_persist_after_client_is_recreated(tmp_path: Path) -> None:
    persist_dir = tmp_path / "chroma"
    first_store = ChromaVectorStore(persist_dir, "test_document_chunks")
    first_store.upsert_chunks([make_record(1)])
    first_store.close()

    second_store = ChromaVectorStore(persist_dir, "test_document_chunks")
    try:
        assert second_store.count_by_document(document_id=1, user_id=1) == 1
    finally:
        second_store.close()


def test_collection_health_reports_total_records(
    vector_store: ChromaVectorStore,
) -> None:
    vector_store.upsert_chunks([make_record(1), make_record(2, document_id=2)])

    health = vector_store.collection_health()

    assert health.healthy is True
    assert health.record_count == 2
