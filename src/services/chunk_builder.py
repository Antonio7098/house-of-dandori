"""Shared course chunk builder utilities for vector indexing."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Literal, Sequence

from src.core.utils import parse_json_fields
from src.services.base_rag_service import sanitize_metadata

Chunk = Dict[str, Any]
ChunkMode = Literal["simple", "narrative"]


def _slugify(value: str | None) -> str:
    if not value:
        return "item"
    sanitized = "".join(char if char.isalnum() else "_" for char in value.lower())
    return sanitized.strip("_") or "item"


def _course_identifier(course: dict) -> str:
    course_id = course.get("id") or course.get("class_id")
    if course_id:
        return str(course_id)
    title = course.get("title") or "course"
    return _slugify(title)


class CourseChunkBuilder:
    """Builds per-course chunks using either simple or narrative strategy."""

    FIELD_MAPPINGS: Sequence[tuple[str, str]] = (
        ("skills", "skill"),
        ("learning_objectives", "objective"),
        ("provided_materials", "material"),
    )

    def __init__(self, mode: ChunkMode = "simple", *, max_chars: int | None = None):
        if mode not in ("simple", "narrative"):
            raise ValueError("mode must be 'simple' or 'narrative'")
        self.mode = mode
        self.max_chars = max_chars

    def build(self, courses: Iterable[dict]) -> List[Chunk]:
        chunks: List[Chunk] = []
        for course in courses:
            parsed = parse_json_fields(course)
            if self.mode == "narrative":
                chunks.extend(self._build_narrative_chunks(parsed))
            else:
                chunks.extend(self._build_simple_chunks(parsed))
        return chunks

    def _metadata(self, course: dict) -> Dict[str, Any]:
        return sanitize_metadata(
            {
                "course_id": course.get("id"),
                "class_id": course.get("class_id"),
                "title": course.get("title"),
                "course_type": course.get("course_type"),
                "location": course.get("location"),
                "instructor": course.get("instructor"),
                "cost": course.get("cost"),
            }
        )

    def _build_simple_chunks(self, course: dict) -> List[Chunk]:
        chunks: List[Chunk] = []
        metadata = self._metadata(course)
        course_uid = _course_identifier(course)

        for field_name, label in self.FIELD_MAPPINGS:
            values = course.get(field_name) or []
            if isinstance(values, str):
                values = [values]
            for idx, value in enumerate(values):
                text = (value or "").strip()
                if not text:
                    continue
                chunk_id = f"{course_uid}_{label}_{idx}"
                chunks.append({"id": chunk_id, "text": text, "metadata": metadata})

        for single_field, label in (("description", "description"), ("title", "title")):
            text = (course.get(single_field) or "").strip()
            if not text:
                continue
            chunk_id = f"{course_uid}_{label}"
            chunks.append({"id": chunk_id, "text": self._truncate(text), "metadata": metadata})

        return chunks

    def _build_narrative_chunks(self, course: dict) -> List[Chunk]:
        title = course.get("title")
        if not title:
            return []

        course_uid = _course_identifier(course)
        metadata = self._metadata(course)

        sections: List[str] = [
            f"Course Title: {title}",
            f"Course Type: {course.get('course_type') or 'Unknown'}",
            f"Instructor: {course.get('instructor') or 'Unknown'}",
            f"Location: {course.get('location') or 'Unknown'}",
        ]

        def _join(values: Sequence[str] | None, label: str) -> None:
            if not values:
                return
            filtered = [value for value in values if value]
            if not filtered:
                return
            sections.append(f"{label}: {', '.join(filtered)}")

        _join(course.get("skills"), "Skills")
        _join(course.get("learning_objectives"), "Learning Objectives")
        _join(course.get("provided_materials"), "Provided Materials")

        description = course.get("description")
        if description:
            sections.append(f"Description: {description}")

        text = ". ".join(part.strip() for part in sections if part)
        chunk_id = f"chunk::{course_uid}"
        return [
            {
                "id": chunk_id,
                "text": self._truncate(text),
                "metadata": metadata,
            }
        ]

    def _truncate(self, text: str) -> str:
        if self.max_chars and len(text) > self.max_chars:
            return text[: self.max_chars].rstrip() + "…"
        return text
