"""GraphRAG service for knowledge-graph-aware retrieval."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests

from src.core.utils import parse_json_fields
from src.services.rag_service import VectorStoreFactory

Predicate = Dict[str, str]


def _course_identifier(course: dict) -> str:
    course_id = course.get("id") or course.get("class_id")
    if course_id:
        return str(course_id)
    title = course.get("title") or "untitled"
    return title.lower().replace(" ", "_")


def build_kg_triples(courses: List[dict]) -> List[dict]:
    predicates: List[Predicate] = [
        {"field": "instructor", "name": "has_instructor"},
        {"field": "course_type", "name": "is_of_type"},
        {"field": "location", "name": "taught_at"},
    ]

    triples: List[dict] = []
    for course in courses:
        course = parse_json_fields(course)
        title = course.get("title")
        if not title:
            continue

        metadata_base = {
            "course_id": course.get("id"),
            "class_id": course.get("class_id"),
            "title": title,
        }
        slug = _course_identifier(course)
        for predicate in predicates:
            value = course.get(predicate["field"])
            if not value:
                continue

            triple_id = f"kg::{slug}::{predicate['name']}::{value}".lower().replace(" ", "_")
            triple_text = f"{title} {predicate['name'].replace('_', ' ')} {value}"
            triples.append(
                {
                    "id": triple_id,
                    "text": triple_text,
                    "metadata": {
                        **metadata_base,
                        "predicate": predicate["name"],
                        "object": value,
                    },
                }
            )

    return triples


def build_course_chunks(courses: List[dict]) -> List[dict]:
    chunks: List[dict] = []
    for course in courses:
        course = parse_json_fields(course)
        title = course.get("title")
        if not title:
            continue

        skills = ", ".join(course.get("skills") or [])
        objectives = "; ".join(course.get("learning_objectives") or [])
        materials = ", ".join(course.get("provided_materials") or [])

        narrative_parts = [
            f"Course Title: {title}",
            f"Course Type: {course.get('course_type') or 'Unknown'}",
            f"Instructor: {course.get('instructor') or 'Unknown'}",
            f"Location: {course.get('location') or 'Unknown'}",
        ]

        if skills:
            narrative_parts.append(f"Skills: {skills}")
        if objectives:
            narrative_parts.append(f"Learning Objectives: {objectives}")
        if materials:
            narrative_parts.append(f"Provided Materials: {materials}")
        if course.get("description"):
            narrative_parts.append(f"Description: {course['description']}")

        text = ". ".join(part.strip() for part in narrative_parts if part)
        chunk_id = f"chunk::{_course_identifier(course)}"
        chunks.append(
            {
                "id": chunk_id,
                "text": text,
                "metadata": {
                    "course_id": course.get("id"),
                    "class_id": course.get("class_id"),
                    "title": title,
                },
            }
        )

    return chunks


class GraphRAGService:
    DEFAULT_KG_COLLECTION = "graph_kg_triples"
    DEFAULT_CHUNK_COLLECTION = "graph_course_chunks"
    DEFAULT_LLM_MODEL = "openai/gpt-4o-mini"

    def __init__(self, provider: Optional[str] = None):
        self.provider_name = provider or os.environ.get("VECTOR_STORE_PROVIDER", "chroma")
        if self.provider_name != "chroma":
            raise ValueError("GraphRAG is currently supported only with the Chroma provider")

        persist_dir = os.environ.get("CHROMA_PERSIST_DIR")
        kg_collection = os.environ.get("GRAPH_RAG_KG_COLLECTION", self.DEFAULT_KG_COLLECTION)
        chunk_collection = os.environ.get(
            "GRAPH_RAG_CHUNK_COLLECTION", self.DEFAULT_CHUNK_COLLECTION
        )

        provider_kwargs: Dict[str, Any] = {}
        if persist_dir:
            provider_kwargs["persist_dir"] = persist_dir

        self.kg_store = VectorStoreFactory.create(
            self.provider_name,
            collection_name=kg_collection,
            **provider_kwargs,
        )
        self.chunk_store = VectorStoreFactory.create(
            self.provider_name,
            collection_name=chunk_collection,
            **provider_kwargs,
        )

        self.llm_model = os.environ.get("GRAPH_RAG_LLM_MODEL", self.DEFAULT_LLM_MODEL)
        self.llm_endpoint = os.environ.get(
            "GRAPH_RAG_LLM_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions"
        )

    def index_courses(self, courses: List[dict]) -> Dict[str, int]:
        kg_triples = build_kg_triples(courses)
        chunks = build_course_chunks(courses)

        self._replace_collection(self.kg_store, kg_triples)
        self._replace_collection(self.chunk_store, chunks)

        return {"kg_triples": len(kg_triples), "course_chunks": len(chunks)}

    def hybrid_search(
        self,
        query: str,
        k_kg: int = 5,
        k_chunks: int = 5,
        include_answer: bool = False,
    ) -> Dict[str, Any]:
        kg_results = self.kg_store.query(query_texts=[query], n_results=k_kg)
        chunk_results = self.chunk_store.query(query_texts=[query], n_results=k_chunks)

        response: Dict[str, Any] = {
            "query": query,
            "kg": self._shape_results(kg_results),
            "chunks": self._shape_results(chunk_results),
        }

        if include_answer:
            response["answer"] = self.generate_answer(query, kg_results, chunk_results)

        return response

    def generate_answer(self, query: str, kg_results: dict, chunk_results: dict) -> Optional[str]:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return None

        kg_docs = self._shape_results(kg_results)["documents"]
        chunk_docs = self._shape_results(chunk_results)["documents"]

        context = "\n".join(filter(None, ["\n".join(kg_docs), "\n".join(chunk_docs)]))
        if not context:
            return None

        payload = {
            "model": self.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that answers questions about the School of "
                        "Dandori courses using provided knowledge graph triples and course chunks."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context}\n\nQuestion: {query}\n",
                },
            ],
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        response = requests.post(self.llm_endpoint, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return None
        return choices[0]["message"]["content"]

    @staticmethod
    def _replace_collection(store, payload: List[dict]) -> None:
        if not payload:
            return
        ids = [item["id"] for item in payload]
        try:
            store.delete(ids)
        except Exception:
            pass
        store.add(
            ids=ids,
            documents=[item["text"] for item in payload],
            metadatas=[item["metadata"] for item in payload],
        )

    @staticmethod
    def _shape_results(results: dict) -> Dict[str, Any]:
        documents = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]
        ids = (results.get("ids") or [[]])[0]
        return {
            "documents": documents,
            "metadatas": metadatas,
            "distances": distances,
            "ids": ids,
            "count": len(documents),
        }


def get_graph_rag_service(provider: Optional[str] = None) -> GraphRAGService:
    return GraphRAGService(provider=provider)
