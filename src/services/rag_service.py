import os

from src.core.vector_store.base import VectorStoreProvider


class VectorStoreFactory:
    _providers = None

    @classmethod
    def _get_providers(cls):
        if cls._providers is None:
            from src.core.vector_store.chroma import ChromaDBProvider
            from src.core.vector_store.vertexai import VertexAIVectorSearchProvider

            cls._providers = {
                "chroma": ChromaDBProvider,
                "vertexai": VertexAIVectorSearchProvider,
            }
        return cls._providers

    @classmethod
    def create(cls, provider: str = None, **kwargs) -> VectorStoreProvider:
        provider = provider or os.environ.get("VECTOR_STORE_PROVIDER", "chroma")
        providers = cls._get_providers()
        if provider not in providers:
            raise ValueError(
                f"Unknown provider: {provider}. Available: {list(providers.keys())}"
            )
        return providers[provider](**kwargs)


class RAGService:
    def __init__(self, provider: str = None, **provider_kwargs):
        self.provider_name = provider or os.environ.get(
            "VECTOR_STORE_PROVIDER", "chroma"
        )
        self.vector_store: VectorStoreProvider = VectorStoreFactory.create(
            self.provider_name, **provider_kwargs
        )

    def build_chunks(self, courses: list[dict]) -> list[dict]:
        chunks = []
        for course in courses:
            course_id = course.get("id")
            metadata = {
                "id": course_id,
                "cost": course.get("cost"),
                "course_type": course.get("course_type"),
                "location": course.get("location"),
                "instructor": course.get("instructor"),
            }

            skills_list = course.get("skills") or []
            skills_text = " .".join(skills_list)
            if skills_text:
                chunks.append(
                    {
                        "id": f"{course_id}_skills",
                        "text": skills_text,
                        "metadata": metadata,
                    }
                )

            objectives_list = course.get("learning_objectives") or []
            objectives_text = " .".join(objectives_list)
            if objectives_text:
                chunks.append(
                    {
                        "id": f"{course_id}_objectives",
                        "text": objectives_text,
                        "metadata": metadata,
                    }
                )

            materials_list = course.get("provided_materials") or []
            materials_text = " .".join(materials_list)
            if materials_text:
                chunks.append(
                    {
                        "id": f"{course_id}_materials",
                        "text": materials_text,
                        "metadata": metadata,
                    }
                )

            description_text = course.get("description")
            if description_text:
                chunks.append(
                    {
                        "id": f"{course_id}_description",
                        "text": description_text,
                        "metadata": metadata,
                    }
                )

            title_text = course.get("title")
            if title_text:
                chunks.append(
                    {
                        "id": f"{course_id}_title",
                        "text": title_text,
                        "metadata": metadata,
                    }
                )

        return chunks

    def index_courses(self, courses: list[dict]) -> None:
        chunks = self.build_chunks(courses)
        if chunks:
            existing_ids = [chunk["id"] for chunk in chunks]
            try:
                self.vector_store.delete(existing_ids)
            except Exception:
                pass

            self.vector_store.add(
                ids=[chunk["id"] for chunk in chunks],
                documents=[chunk["text"] for chunk in chunks],
                metadatas=[chunk["metadata"] for chunk in chunks],
            )

    def search(self, query: str, n_results: int = 5) -> dict:
        return self.vector_store.query(query_texts=[query], n_results=n_results)

    def close(self) -> None:
        self.vector_store.close()


def get_rag_service(provider: str = None) -> RAGService:
    return RAGService(provider=provider)
