from abc import ABC, abstractmethod
from typing import Any


class VectorStoreProvider(ABC):
    @abstractmethod
    def add(self, ids: list[str], documents: list[str], metadatas: list[dict]) -> None:
        pass

    @abstractmethod
    def delete(self, ids: list[str]) -> None:
        pass

    @abstractmethod
    def query(self, query_texts: list[str], n_results: int) -> dict:
        pass

    @abstractmethod
    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        pass

    @abstractmethod
    def close(self) -> None:
        pass


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        pass
