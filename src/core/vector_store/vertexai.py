import os
from typing import Any

from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel

from src.core.vector_store.base import VectorStoreProvider, EmbeddingProvider


class VertexAIEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        model_name: str = "text-embedding-005",
        project: str = None,
        location: str = "us-central1",
    ):
        self.project = project or os.environ.get("GCP_PROJECT_ID")
        self.location = location or os.environ.get("GCP_LOCATION", "us-central1")

        if not self.project:
            raise ValueError("GCP_PROJECT_ID environment variable is required")

        aiplatform.init(project=self.project, location=self.location)
        self.model = TextEmbeddingModel.from_pretrained(model_name)
        self.dimensions = 768

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.get_embeddings(texts)
        return [e.values for e in embeddings]


class VertexAIVectorSearchProvider(VectorStoreProvider):
    def __init__(
        self,
        index_id: str = None,
        index_endpoint_id: str = None,
        project: str = None,
        location: str = "us-central1",
        embedding_model: str = "text-embedding-005",
    ):
        from google.cloud import aiplatform_v1
        from google.cloud.aiplatform_v1 import types

        self.project = project or os.environ.get("GCP_PROJECT_ID")
        self.location = location or os.environ.get("GCP_LOCATION", "us-central1")
        self.index_id = index_id or os.environ.get("VERTEX_AI_INDEX_ID")
        self.index_endpoint_id = index_endpoint_id or os.environ.get(
            "VERTEX_AI_INDEX_ENDPOINT_ID"
        )

        if not self.project:
            raise ValueError("GCP_PROJECT_ID environment variable is required")

        aiplatform.init(project=self.project, location=self.location)

        self.embedding_provider = VertexAIEmbeddingProvider(
            model_name=embedding_model, project=self.project, location=self.location
        )
        self.dimensions = 768

        self._index = None
        self._client = None

        if self.index_id:
            self._client = aiplatform_v1.IndexServiceClient()
            self._index = self._client.get_index(
                name=f"projects/{self.project}/locations/{self.location}/indexes/{self.index_id}"
            )

    @property
    def index(self):
        if self._index is None and self.index_id:
            self._client = aiplatform_v1.IndexServiceClient()
            self._index = self._client.get_index(
                name=f"projects/{self.project}/locations/{self.location}/indexes/{self.index_id}"
            )
        return self._index

    def add(self, ids: list[str], documents: list[str], metadatas: list[dict]) -> None:
        if not self.index:
            raise RuntimeError(
                "No index configured. Set VERTEX_AI_INDEX_ID environment variable or provide index_id"
            )

        embeddings = self.get_embeddings(documents)

        from google.cloud import aiplatform_v1
        from google.cloud.aiplatform_v1 import types

        datapoints = []
        for i, doc_id in enumerate(ids):
            datapoint = types.IndexDatapoint(
                datapoint_id=doc_id,
                feature_vector=embeddings[i],
                RESTRICT=metadatas[i] if metadatas[i] else {},
            )
            datapoints.append(datapoint)

        self.index.upsert_datapoints(datapoints=datapoints)

    def delete(self, ids: list[str]) -> None:
        if not self.index:
            raise RuntimeError(
                "No index configured. Set VERTEX_AI_INDEX_ID environment variable or provide index_id"
            )

        from google.cloud import aiplatform_v1

        self.index.remove_datapoints(datapoint_ids=ids)

    def query(self, query_texts: list[str], n_results: int = 5) -> dict:
        if not self.index_endpoint_id:
            raise RuntimeError(
                "No index endpoint configured. Set VERTEX_AI_INDEX_ENDPOINT_ID environment variable"
            )

        from google.cloud import aiplatform_v1
        from google.cloud.aiplatform_v1 import types

        query_embedding = self.get_embeddings(query_texts)[0]

        client = aiplatform_v1.MatchServiceClient()
        request = types.FindNeighborsRequest(
            index_endpoint=self._get_index_endpoint_name(),
            query={
                "datapoint_id": "query",
                "feature_vector": query_embedding,
            },
            neighbor_count=n_results,
        )

        response = client.find_neighbors(request)

        results = {
            "ids": [[n.datapoint_id for n in response.neighbors]]
            if response.neighbors
            else [[]],
            "distances": [[n.distance for n in response.neighbors]]
            if response.neighbors
            else [[]],
            "documents": [[] for _ in query_texts],
            "metadatas": [[] for _ in query_texts],
        }

        return results

    def _get_index_endpoint_name(self):
        return f"projects/{self.project}/locations/{self.location}/indexEndpoints/{self.index_endpoint_id}"

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return self.embedding_provider.embed(texts)

    def close(self) -> None:
        pass
