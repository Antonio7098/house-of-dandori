import os
from typing import Optional

from src.services.base_rag_service import BaseRAGService
from src.services.chunk_builder import CourseChunkBuilder

class RAGService(BaseRAGService):
    def __init__(self, provider: Optional[str] = None, **kwargs):
        super().__init__(provider=provider or os.environ.get("VECTOR_STORE_PROVIDER", "qdrant"), **kwargs)
        self.vector_store = self.create_collection()
        self._chunk_builder = CourseChunkBuilder(mode="simple")

    def build_chunks(self, courses: list[dict]) -> list[dict]:
        return self._chunk_builder.build(courses)

    def index_courses(self, courses: list[dict]) -> None:
        chunks = self.build_chunks(courses)
        if chunks:
            self._replace_collection(self.vector_store, chunks)

    def upsert_course(self, course: dict | None) -> None:
        if not course:
            return
        self.index_courses([course])

    def delete_course(self, course: dict | None) -> None:
        if not course:
            return
        chunks = self.build_chunks([course])
        if not chunks:
            return
        ids = [chunk["id"] for chunk in chunks]
        if ids:
            self.vector_store.delete(ids)

    def search(self, query: str, n_results: int = 5) -> dict:
        results = self.vector_store.query(query_texts=[query], n_results=n_results)
        return self._shape_results(results)


def get_rag_service(provider: str = None) -> RAGService:
    return RAGService(provider=provider)
