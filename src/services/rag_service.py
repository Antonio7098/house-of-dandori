from src.services.base_rag_service import BaseRAGService, sanitize_metadata
from src.services.chunk_builder import CourseChunkBuilder
import os
from typing import Optional

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

    def search(self, query: str, n_results: int = 5) -> dict:
        results = self.vector_store.query(query_texts=[query], n_results=n_results)
        return self._shape_results(results)


def get_rag_service(provider: str = None) -> RAGService:
    return RAGService(provider=provider)
