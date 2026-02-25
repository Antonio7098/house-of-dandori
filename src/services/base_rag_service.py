"""Base RAG service utilities shared across vector-based services."""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.vector_store.base import VectorStoreProvider


def ensure_chroma_persist_dir() -> str:
    """Ensure the Chroma persistence directory exists and return its path."""
    persist_dir = os.environ.get("CHROMA_PERSIST_DIR")
    if persist_dir:
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        return persist_dir

    default_dir = Path(__file__).resolve().parent.parent.parent / "chroma_data"
    default_dir.mkdir(parents=True, exist_ok=True)
    os.environ["CHROMA_PERSIST_DIR"] = str(default_dir)
    return str(default_dir)


class VectorStoreFactory:
    _providers: Optional[Dict[str, type]] = None

    @classmethod
    def _get_providers(cls) -> Dict[str, type]:
        if cls._providers is None:
            from src.core.vector_store.chroma import ChromaDBProvider
            from src.core.vector_store.qdrant import QdrantVectorStoreProvider
            from src.core.vector_store.vertexai import VertexAIVectorSearchProvider

            cls._providers = {
                "chroma": ChromaDBProvider,
                "qdrant": QdrantVectorStoreProvider,
                "vertexai": VertexAIVectorSearchProvider,
            }
        return cls._providers

    @classmethod
    def create(cls, provider: Optional[str] = None, **kwargs) -> VectorStoreProvider:
        provider = provider or os.environ.get("VECTOR_STORE_PROVIDER", "chroma")
        providers = cls._get_providers()
        if provider not in providers:
            raise ValueError(
                f"Unknown provider: {provider}. Available: {list(providers.keys())}"
            )
        return providers[provider](**kwargs)

    @classmethod
    def register_provider(cls, name: str, provider_class: type) -> None:
        if cls._providers is None:
            cls._providers = {}
        cls._providers[name] = provider_class


def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        else:
            sanitized[key] = str(value)
    return sanitized


class BaseRAGService(ABC):
    DEFAULT_BATCH_SIZE = 2000

    def __init__(
        self,
        provider: Optional[str] = None,
        batch_size: Optional[int] = None,
        **provider_kwargs,
    ):
        self.provider_name = provider or os.environ.get(
            "VECTOR_STORE_PROVIDER", "chroma"
        )
        self._provider_kwargs = provider_kwargs
        self.batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        self._stores: List[VectorStoreProvider] = []

    def _create_store(
        self,
        collection_name: Optional[str] = None,
        **extra_kwargs,
    ) -> VectorStoreProvider:
        kwargs = {**self._provider_kwargs, **extra_kwargs}
        if (
            "persist_dir" not in kwargs
            and self.provider_name == "chroma"
        ):
            kwargs["persist_dir"] = ensure_chroma_persist_dir()
        if collection_name:
            kwargs["collection_name"] = collection_name

        store = VectorStoreFactory.create(self.provider_name, **kwargs)
        self._stores.append(store)
        return store

    def create_collection(
        self,
        collection_name: Optional[str] = None,
        **extra_kwargs,
    ) -> VectorStoreProvider:
        """Public helper for creating and tracking a vector store collection."""
        return self._create_store(collection_name=collection_name, **extra_kwargs)

    def _replace_collection(
        self,
        store: VectorStoreProvider,
        payload: List[Dict[str, Any]],
    ) -> None:
        if not payload:
            return
        ids = [item["id"] for item in payload]
        documents = [item["text"] for item in payload]
        metadatas = [item["metadata"] for item in payload]
        try:
            store.delete(ids)
        except Exception:
            pass

        for start in range(0, len(ids), self.batch_size):
            end = start + self.batch_size
            store.add(
                ids=ids[start:end],
                documents=documents[start:end],
                metadatas=metadatas[start:end],
            )

    @staticmethod
    def _shape_results(results: dict) -> Dict[str, Any]:
        def _nested(value: Optional[List[Any]]) -> List[List[Any]]:
            if not value:
                return [[]]
            if isinstance(value[0], list):
                return value  # already nested
            return [value]

        documents_list = _nested(results.get("documents"))
        metadatas_list = _nested(results.get("metadatas"))
        distances_list = _nested(results.get("distances"))
        ids_list = _nested(results.get("ids"))

        documents = documents_list[0]
        metadatas = metadatas_list[0]
        distances = distances_list[0]
        ids = ids_list[0]
        return {
            "documents": documents,
            "metadatas": metadatas,
            "distances": distances,
            "ids": ids,
            "count": len(documents),
        }

    @abstractmethod
    def index_courses(self, courses: List[dict]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, n_results: int = 5) -> dict:
        raise NotImplementedError

    def close(self) -> None:
        for store in self._stores:
            if hasattr(store, "close"):
                try:
                    store.close()
                except Exception:
                    pass
        self._stores.clear()

    def close_all(self) -> None:
        """Explicit alias for closing tracked vector stores."""
        self.close()
