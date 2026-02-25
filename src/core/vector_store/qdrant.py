"""Qdrant vector store provider implementation."""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, List

from src.core.vector_store.base import VectorStoreProvider
from src.core.vector_store.embeddings import OpenRouterEmbedder

DEFAULT_DIMENSIONS = 768
DEFAULT_MAX_POINTS_PER_BATCH = 200


def _to_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _sanitize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {}
    for key, value in payload.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool, list, dict)):
            sanitized[key] = value
        else:
            sanitized[key] = str(value)
    return sanitized


class QdrantVectorStoreProvider(VectorStoreProvider):
    def __init__(
        self,
        collection_name: str = "courses",
        embedding_model: str = "google/gemini-embedding-001",
        url: str | None = None,
        api_key: str | None = None,
        prefer_grpc: bool | None = None,
        timeout: int = 60,
        max_points_per_batch: int = DEFAULT_MAX_POINTS_PER_BATCH,
    ) -> None:
        from qdrant_client import QdrantClient  # lazy import per provider guidelines
        from qdrant_client.http import models as qmodels

        self._qmodels = qmodels
        api_token = api_key or os.environ.get("QDRANT_API_KEY")
        endpoint = url or os.environ.get("QDRANT_URL")
        if not endpoint:
            raise ValueError("QDRANT_URL environment variable is required for qdrant provider")

        env_collection = os.environ.get("QDRANT_COLLECTION")
        self.collection_name = env_collection or collection_name
        self.distance = qmodels.Distance.COSINE
        self.max_points_per_batch = max(1, max_points_per_batch)
        self._id_namespace = uuid.uuid5(uuid.NAMESPACE_DNS, "dandori-qdrant")

        if prefer_grpc is None:
            prefer_grpc = _to_bool(os.environ.get("QDRANT_PREFER_GRPC"))

        client_kwargs: Dict[str, Any] = {"url": endpoint, "api_key": api_token, "timeout": timeout}
        if prefer_grpc is not None:
            client_kwargs["prefer_grpc"] = prefer_grpc

        self.client = QdrantClient(**client_kwargs)

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required for qdrant provider")

        self.embedder = OpenRouterEmbedder(api_key=api_key, model=embedding_model)
        self.dimensions = self._resolve_dimensions()
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if self.client.collection_exists(self.collection_name):
            info = self.client.get_collection(self.collection_name)
            try:
                existing_size = info.config.params.vectors.size  # type: ignore[attr-defined]
            except AttributeError:
                existing_size = None
            if existing_size != self.dimensions:
                self.client.delete_collection(self.collection_name)
            else:
                return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=self._qmodels.VectorParams(size=self.dimensions, distance=self.distance),
        )

    def add(self, ids: list[str], documents: list[str], metadatas: list[dict]) -> None:
        embeddings = self.get_embeddings(documents)
        points = []
        for idx, vector in enumerate(embeddings):
            payload = {
                **(metadatas[idx] or {}),
                "document": documents[idx],
                "chunk_id": ids[idx],
            }
            points.append(
                self._qmodels.PointStruct(
                    id=self._normalize_id(ids[idx]),
                    vector=vector,
                    payload=_sanitize_payload(payload),
                )
            )
        for start in range(0, len(points), self.max_points_per_batch):
            batch = points[start : start + self.max_points_per_batch]
            self.client.upsert(collection_name=self.collection_name, wait=True, points=batch)

    def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        selector = self._qmodels.PointIdsList(
            points=[self._normalize_id(value) for value in ids]
        )
        self.client.delete(collection_name=self.collection_name, points_selector=selector, wait=True)

    def query(self, query_texts: list[str], n_results: int = 5) -> dict:
        results = {"ids": [], "documents": [], "metadatas": [], "distances": []}
        for text in query_texts:
            vector = self.get_embeddings([text])[0]
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                with_payload=True,
                limit=n_results,
            )
            hits = response.points if hasattr(response, "points") else response
            ids = []
            documents = []
            metadatas: List[Dict[str, Any]] = []
            distances = []
            for hit in hits:
                ids.append(str(hit.id))
                payload = getattr(hit, "payload", None) or {}
                documents.append(payload.get("document", ""))
                metadatas.append({k: v for k, v in payload.items() if k != "document"})
                distances.append(float(getattr(hit, "score", 0.0)))
            results["ids"].append(ids)
            results["documents"].append(documents)
            results["metadatas"].append(metadatas)
            results["distances"].append(distances)
        return results

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return self.embedder(texts) if texts else []

    def close(self) -> None:
        try:
            self.client.close()
        except Exception:
            pass

    def _normalize_id(self, value: str) -> str:
        if not isinstance(value, str):
            value = str(value)
        return str(uuid.uuid5(self._id_namespace, value))

    def _resolve_dimensions(self) -> int:
        override = os.environ.get("QDRANT_VECTOR_SIZE")
        if override:
            try:
                return int(override)
            except ValueError:
                pass

        try:
            sample = self.embedder(["dimension probe"])
        except Exception:
            return DEFAULT_DIMENSIONS

        first_vector = None
        try:
            first_vector = sample[0]
        except (TypeError, IndexError):
            first_vector = None

        if first_vector is None:
            return DEFAULT_DIMENSIONS

        try:
            return len(first_vector)
        except TypeError:
            try:
                materialized = list(first_vector)
            except TypeError:
                return DEFAULT_DIMENSIONS
            return len(materialized)
