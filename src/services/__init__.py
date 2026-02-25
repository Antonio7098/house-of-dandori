"""Unified service factory for vector and graph retrieval modes."""
from __future__ import annotations

from typing import Literal, Optional, Union

from src.services.base_rag_service import BaseRAGService
from src.services.graph_rag_service import GraphRAGService, get_graph_rag_service
from src.services.rag_service import RAGService, get_rag_service


def get_service(
    mode: Literal["vector", "graph"] = "vector",
    provider: Optional[str] = None,
    **service_kwargs,
) -> Union[RAGService, GraphRAGService, BaseRAGService]:
    """Return the appropriate retrieval service based on mode."""

    if mode == "graph":
        return get_graph_rag_service(provider=provider, **service_kwargs)
    return get_rag_service(provider=provider)
