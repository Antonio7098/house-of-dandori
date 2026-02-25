"""GraphRAG service orchestrating KG triple indexing and hybrid retrieval."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from src.services.base_rag_service import BaseRAGService
from src.services.graph_builders import (
    build_course_chunks,
    build_graph_relationships,
    build_kg_triples,
)
from src.services.graph_store import GraphStore, create_graph_store


class GraphRAGService(BaseRAGService):
    DEFAULT_KG_COLLECTION = "graph_kg_triples"
    DEFAULT_CHUNK_COLLECTION = "graph_course_chunks"

    def __init__(self, provider: Optional[str] = None):
        super().__init__(provider=provider)
        if self.provider_name != "chroma":
            raise ValueError(
                "GraphRAG is currently supported only with the Chroma provider"
            )

        kg_collection = os.environ.get(
            "GRAPH_RAG_KG_COLLECTION", self.DEFAULT_KG_COLLECTION
        )
        chunk_collection = os.environ.get(
            "GRAPH_RAG_CHUNK_COLLECTION", self.DEFAULT_CHUNK_COLLECTION
        )

        self.kg_store = self._create_store(collection_name=kg_collection)
        self.chunk_store = self._create_store(collection_name=chunk_collection)

        self.graph_store: Optional[GraphStore] = None
        self.neo4j_enabled = (
            os.environ.get("GRAPH_RAG_USE_NEO4J", "false").lower() == "true"
        )
        if self.neo4j_enabled:
            neo4j_password = os.environ.get("NEO4J_PASSWORD")
            if not neo4j_password:
                raise ValueError(
                    "NEO4J_PASSWORD must be set when GRAPH_RAG_USE_NEO4J=true"
                )
            neo4j_batch = os.environ.get("GRAPH_RAG_NEO4J_BATCH_SIZE")
            try:
                neo4j_batch_size = max(1, int(neo4j_batch)) if neo4j_batch else 500
            except ValueError:
                neo4j_batch_size = 500
            self.graph_store = create_graph_store(
                backend="neo4j",
                uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
                user=os.environ.get("NEO4J_USER", "neo4j"),
                password=neo4j_password,
                batch_size=neo4j_batch_size,
            )

    def index_courses(self, courses: List[dict]) -> Dict[str, int]:
        kg_triples = build_kg_triples(courses)
        chunks = build_course_chunks(courses)
        graph_relationships = build_graph_relationships(kg_triples)

        self._replace_collection(self.kg_store, kg_triples)
        self._replace_collection(self.chunk_store, chunks)
        if self.graph_store and graph_relationships:
            self.graph_store.replace_graph(graph_relationships)

        return {
            "kg_triples": len(kg_triples),
            "course_chunks": len(chunks),
            "graph_relationships": len(graph_relationships),
        }

    def search(self, query: str, n_results: int = 5) -> dict:
        return self.hybrid_search(query, k_kg=n_results, k_chunks=n_results)

    def hybrid_search(
        self,
        query: str,
        k_kg: int = 5,
        k_chunks: int = 5,
    ) -> Dict[str, Any]:
        kg_results = self.kg_store.query(query_texts=[query], n_results=k_kg)
        chunk_results = self.chunk_store.query(query_texts=[query], n_results=k_chunks)

        return {
            "query": query,
            "kg": self._shape_results(kg_results),
            "chunks": self._shape_results(chunk_results),
        }

    def graph_neighbors(self, value: str, limit: int = 25) -> Dict[str, Any]:
        if not self.graph_store:
            raise ValueError(
                "Graph neighbors require Neo4j. Set GRAPH_RAG_USE_NEO4J=true."
            )
        limit = max(1, min(limit, 100))
        return self.graph_store.neighbors(value, limit)

    def close(self) -> None:
        super().close()
        if self.graph_store:
            self.graph_store.close()


def get_graph_rag_service(provider: Optional[str] = None) -> GraphRAGService:
    return GraphRAGService(provider=provider)
