from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, cast

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.api.types import Metadata, Where

from app.ai.vector_store.base import (
    CollectionHealth,
    SearchResult,
    VectorRecord,
    VectorStore,
    VectorStoreConfigurationError,
    VectorStoreInputError,
    VectorStoreOperationError,
)


class _ClosableClient(Protocol):
    def close(self) -> None: ...


class ChromaVectorStore(VectorStore):
    def __init__(self, persist_dir: Path, collection_name: str) -> None:
        if not collection_name.strip():
            raise VectorStoreConfigurationError(
                "CHROMA_COLLECTION_NAME is not configured"
            )

        persist_dir.expanduser().resolve().mkdir(parents=True, exist_ok=True)
        client: ClientAPI | None = None
        try:
            client = chromadb.PersistentClient(
                path=persist_dir.expanduser().resolve()
            )
            collection: Collection = client.get_or_create_collection(
                name=collection_name.strip(),
                configuration={"hnsw": {"space": "cosine"}},
                embedding_function=None,
            )
            self._verify_cosine_distance(collection)
            self._client = client
            self._collection = collection
        except VectorStoreConfigurationError:
            if client is not None:
                cast(_ClosableClient, client).close()
            raise
        except Exception as exc:
            if client is not None:
                cast(_ClosableClient, client).close()
            raise VectorStoreConfigurationError(
                "Unable to initialize ChromaDB collection"
            ) from exc

    def upsert_chunks(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        self._validate_records(records)

        try:
            self._collection.upsert(
                ids=[self._vector_id(record.chunk_id) for record in records],
                embeddings=[record.embedding for record in records],
                documents=[record.content for record in records],
                metadatas=[self._metadata(record) for record in records],
            )
        except Exception as exc:
            raise VectorStoreOperationError("Unable to write vectors") from exc

    def delete_by_document(self, document_id: int, user_id: int) -> None:
        try:
            self._collection.delete(
                where=self._combined_filter(
                    "user_id",
                    user_id,
                    "document_id",
                    document_id,
                )
            )
        except Exception as exc:
            raise VectorStoreOperationError("Unable to delete document vectors") from exc

    def delete_by_knowledge_base(
        self,
        knowledge_base_id: int,
        user_id: int,
    ) -> None:
        try:
            self._collection.delete(
                where=self._combined_filter(
                    "user_id",
                    user_id,
                    "knowledge_base_id",
                    knowledge_base_id,
                )
            )
        except Exception as exc:
            raise VectorStoreOperationError(
                "Unable to delete knowledge base vectors"
            ) from exc

    def search(
        self,
        query_vector: list[float],
        user_id: int,
        knowledge_base_id: int,
        top_k: int,
        embedding_model: str | None = None,
    ) -> list[SearchResult]:
        self._validate_vector(query_vector)
        if not 1 <= top_k <= 20:
            raise VectorStoreInputError("top_k must be between 1 and 20")

        try:
            response = self._collection.query(
                query_embeddings=[query_vector],
                n_results=top_k,
                where=self._search_filter(
                    user_id=user_id,
                    knowledge_base_id=knowledge_base_id,
                    embedding_model=embedding_model,
                ),
                include=["documents", "metadatas", "distances"],
            )
            return self._map_search_response(response)
        except VectorStoreOperationError:
            raise
        except Exception as exc:
            raise VectorStoreOperationError("Unable to search vectors") from exc

    def count_by_document(self, document_id: int, user_id: int) -> int:
        try:
            response = self._collection.get(
                where=self._combined_filter(
                    "user_id",
                    user_id,
                    "document_id",
                    document_id,
                ),
                include=[],
            )
            return len(response["ids"])
        except Exception as exc:
            raise VectorStoreOperationError("Unable to count document vectors") from exc

    def collection_health(self) -> CollectionHealth:
        try:
            self._client.heartbeat()
            return CollectionHealth(
                healthy=True,
                record_count=self._collection.count(),
            )
        except Exception as exc:
            raise VectorStoreOperationError("ChromaDB collection is unavailable") from exc

    def close(self) -> None:
        cast(_ClosableClient, self._client).close()

    @staticmethod
    def _verify_cosine_distance(collection: Collection) -> None:
        hnsw_config = collection.configuration.get("hnsw")
        if not isinstance(hnsw_config, Mapping) or hnsw_config.get("space") != "cosine":
            raise VectorStoreConfigurationError(
                "Existing ChromaDB collection does not use cosine distance"
            )

    @staticmethod
    def _vector_id(chunk_id: int) -> str:
        return f"chunk:{chunk_id}"

    @staticmethod
    def _metadata(record: VectorRecord) -> Metadata:
        metadata: Metadata = {
            "user_id": record.user_id,
            "knowledge_base_id": record.knowledge_base_id,
            "document_id": record.document_id,
            "chunk_id": record.chunk_id,
            "chunk_index": record.chunk_index,
            "filename": record.filename,
            "content_hash": record.content_hash,
            "embedding_model": record.embedding_model,
        }
        if record.page_number is not None:
            metadata["page_number"] = record.page_number
        if record.section_title:
            metadata["section_title"] = record.section_title
        return metadata

    @staticmethod
    def _combined_filter(
        first_key: str,
        first_value: int,
        second_key: str,
        second_value: int,
    ) -> Where:
        return {
            "$and": [
                {first_key: {"$eq": first_value}},
                {second_key: {"$eq": second_value}},
            ]
        }

    @staticmethod
    def _search_filter(
        *,
        user_id: int,
        knowledge_base_id: int,
        embedding_model: str | None,
    ) -> Where:
        filters: list[Where] = [
            {"user_id": {"$eq": user_id}},
            {"knowledge_base_id": {"$eq": knowledge_base_id}},
        ]
        if embedding_model is not None:
            filters.append({"embedding_model": {"$eq": embedding_model}})
        return {"$and": filters}

    @staticmethod
    def _validate_records(records: list[VectorRecord]) -> None:
        expected_dimension: int | None = None
        for record in records:
            if record.chunk_id < 1 or record.document_id < 1:
                raise VectorStoreInputError("Vector record IDs must be positive")
            if not record.content.strip():
                raise VectorStoreInputError("Vector record content cannot be empty")
            ChromaVectorStore._validate_vector(record.embedding)
            if expected_dimension is None:
                expected_dimension = len(record.embedding)
            elif len(record.embedding) != expected_dimension:
                raise VectorStoreInputError(
                    "Vector record dimensions must be consistent"
                )

    @staticmethod
    def _validate_vector(vector: list[float]) -> None:
        if not vector or any(
            isinstance(value, bool) or not isinstance(value, (int, float))
            for value in vector
        ):
            raise VectorStoreInputError("Vector must contain numeric values")

    @staticmethod
    def _map_search_response(response: Mapping[str, object]) -> list[SearchResult]:
        raw_ids = response.get("ids")
        if not isinstance(raw_ids, list) or not raw_ids or not raw_ids[0]:
            return []

        raw_documents = response.get("documents")
        raw_metadatas = response.get("metadatas")
        raw_distances = response.get("distances")
        if not all(
            isinstance(value, list) and value
            for value in (raw_documents, raw_metadatas, raw_distances)
        ):
            raise VectorStoreOperationError("ChromaDB returned incomplete search data")

        documents = cast(list[str | None], raw_documents[0])
        metadatas = cast(list[Metadata | None], raw_metadatas[0])
        distances = cast(list[float | None], raw_distances[0])
        result_count = len(raw_ids[0])
        if not (
            len(documents) == len(metadatas) == len(distances) == result_count
        ):
            raise VectorStoreOperationError("ChromaDB returned inconsistent search data")

        results: list[SearchResult] = []
        for document, metadata, distance in zip(
            documents,
            metadatas,
            distances,
            strict=True,
        ):
            if document is None or metadata is None or distance is None:
                raise VectorStoreOperationError("ChromaDB returned incomplete search data")
            results.append(
                SearchResult(
                    chunk_id=ChromaVectorStore._required_int(metadata, "chunk_id"),
                    document_id=ChromaVectorStore._required_int(
                        metadata,
                        "document_id",
                    ),
                    filename=ChromaVectorStore._required_str(metadata, "filename"),
                    content=document,
                    chunk_index=ChromaVectorStore._required_int(
                        metadata,
                        "chunk_index",
                    ),
                    page_number=ChromaVectorStore._optional_int(
                        metadata,
                        "page_number",
                    ),
                    section_title=ChromaVectorStore._optional_str(
                        metadata,
                        "section_title",
                    ),
                    distance=float(distance),
                )
            )
        return results

    @staticmethod
    def _required_int(metadata: Metadata, key: str) -> int:
        value = metadata.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise VectorStoreOperationError(f"ChromaDB metadata {key} is invalid")
        return value

    @staticmethod
    def _required_str(metadata: Metadata, key: str) -> str:
        value = metadata.get(key)
        if not isinstance(value, str):
            raise VectorStoreOperationError(f"ChromaDB metadata {key} is invalid")
        return value

    @staticmethod
    def _optional_int(metadata: Metadata, key: str) -> int | None:
        if key not in metadata:
            return None
        return ChromaVectorStore._required_int(metadata, key)

    @staticmethod
    def _optional_str(metadata: Metadata, key: str) -> str | None:
        if key not in metadata:
            return None
        return ChromaVectorStore._required_str(metadata, key)
