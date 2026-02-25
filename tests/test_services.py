"""Service-layer unit tests covering chunk builder and graph store registry."""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

from src.services.base_rag_service import BaseRAGService
from src.services.chunk_builder import CourseChunkBuilder
from src.services.graph_rag_service import GraphRAGService
from src.services.graph_store import GraphStore, create_graph_store, register_graph_backend


def _sample_course() -> Dict[str, Any]:
    return {
        "id": "course-123",
        "title": "Waffle Weaving Basics",
        "skills": ["Pattern planning", "Batter control"],
        "learning_objectives": "Serve artful waffles",
        "provided_materials": ["Cast-iron griddle"],
        "description": "Learn to weave waffles with flair.",
        "course_type": "Culinary Arts",
        "location": "London",
        "instructor": "Ada Calm",
    }


def test_simple_chunk_builder_emits_per_item_chunks() -> None:
    builder = CourseChunkBuilder(mode="simple")
    chunks = builder.build([_sample_course()])

    texts = {chunk["text"] for chunk in chunks}
    assert "Pattern planning" in texts
    assert "Batter control" in texts
    assert "Serve artful waffles" in texts  # objective should remain separate
    assert any(chunk["id"].endswith("_material_0") for chunk in chunks)


def test_narrative_chunk_builder_returns_single_chunk() -> None:
    builder = CourseChunkBuilder(mode="narrative")
    chunks = builder.build([_sample_course()])

    assert len(chunks) == 1
    text = chunks[0]["text"]
    assert "Course Title: Waffle Weaving Basics" in text
    assert "Skills: Pattern planning, Batter control" in text
    assert "Learning Objectives:" in text


class _DummyGraphStore(GraphStore):
    def __init__(self) -> None:
        self.closed = False
        self.replacements: List[List[Dict[str, Any]]] = []

    def close(self) -> None:  # pragma: no cover - trivial
        self.closed = True

    def replace_graph(self, relationships: List[Dict[str, Any]]) -> None:
        self.replacements.append(relationships)

    def get_entity(self, value: str) -> Dict[str, Any] | None:
        return {"uid": value, "name": value.title(), "properties": {}}

    def neighbors(self, value: str, limit: int = 25) -> Dict[str, Any]:
        return {"found": True, "entity": value, "neighbors": []}


def test_custom_graph_backend_registration() -> None:
    backend_name = "dummy_graph_backend"
    register_graph_backend(backend_name, lambda **kwargs: _DummyGraphStore())

    store = create_graph_store(backend=backend_name)
    assert isinstance(store, _DummyGraphStore)


def test_shape_results_normalizes_flat_lists() -> None:
    raw_results = {
        "documents": ["doc-a", "doc-b"],
        "metadatas": [{"course_id": 1}, {"course_id": 2}],
        "distances": [0.1, 0.2],
        "ids": ["a", "b"],
    }

    shaped = BaseRAGService._shape_results(raw_results)

    assert shaped["documents"] == ["doc-a", "doc-b"]
    assert shaped["metadatas"][0]["course_id"] == 1
    assert shaped["metadatas"][1]["course_id"] == 2
    assert shaped["distances"] == [0.1, 0.2]
    assert shaped["ids"] == ["a", "b"]
    assert shaped["count"] == 2


def test_graph_rag_requires_chroma_provider() -> None:
    with pytest.raises(ValueError, match="GraphRAG is currently supported only with the Chroma provider"):
        GraphRAGService(provider="qdrant")
