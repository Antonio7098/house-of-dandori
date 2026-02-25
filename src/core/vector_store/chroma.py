import logging
import os
from typing import Any

import chromadb
from chromadb.config import Settings

from src.core.vector_store.base import VectorStoreProvider
from src.core.vector_store.embeddings import OpenRouterEmbedder


class ChromaDBProvider(VectorStoreProvider):
    def __init__(
        self,
        collection_name: str = "courses",
        persist_dir: str | None = None,
        embedding_model: str = "google/gemini-embedding-001",
    ):
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")

        self.collection_name = collection_name
        self.persist_dir = persist_dir
        self.embedding_model = embedding_model
        self.embedder = OpenRouterEmbedder(
            api_key=api_key,
            model=embedding_model,
        )

        self.client = self._create_client()

        self._ensure_collection()

    def _ensure_collection(self) -> None:
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedder,
        )

    def _create_client(self):
        base_settings = {
            "anonymized_telemetry": False,
        }

        if self.persist_dir:
            settings = Settings(
                **base_settings,
                is_persistent=True,
                persist_directory=self.persist_dir,
                allow_reset=True,
            )
            try:
                return chromadb.PersistentClient(path=self.persist_dir, settings=settings)
            except ValueError as err:
                logging.warning(
                    "Failed to initialize persistent Chroma client at %s (%s). Falling back to in-memory store.",
                    self.persist_dir,
                    err,
                )

        # fallback to in-memory client
        fallback_settings = Settings(**base_settings)
        return chromadb.Client(fallback_settings)

    def add(self, ids: list[str], documents: list[str], metadatas: list[dict]) -> None:
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    def delete(self, ids: list[str]) -> None:
        self.collection.delete(ids=ids)

    def query(self, query_texts: list[str], n_results: int = 5) -> dict:
        return self.collection.query(query_texts=query_texts, n_results=n_results)

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return self.collection._embedding_function(texts)

    def close(self) -> None:
        pass

    def reset(self) -> None:
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        self._ensure_collection()
