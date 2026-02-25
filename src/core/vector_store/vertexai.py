import os
from typing import Any, Optional

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
        # Batch embeddings to respect API limits (250 texts per request)
        batch_size = 50
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = self.model.get_embeddings(batch)
            all_embeddings.extend([e.values for e in embeddings])
        
        return all_embeddings



class VertexAIVectorSearchProvider(VectorStoreProvider):
    """
    Vertex AI Vector Search provider supporting both V1 (Index/Endpoint) and V2 (Collection) APIs.
    
    V2 API (recommended):
        - Uses Collections to store Data Objects with vectors, metadata, and content
        - Simpler unified data model
        - Set api_version="v2" and provide collection_id
        
    V1 API (legacy):
        - Uses Indexes deployed to Endpoints with separate document storage
        - Provide index_id and index_endpoint_id
    """
    
    def __init__(
        self,
        collection_id: str = None,
        index_id: str = None,
        index_endpoint_id: str = None,
        project: str = None,
        location: str = "us-central1",
        embedding_model: str = "text-embedding-005",
        api_version: str = None,
    ):
        self.project = project or os.environ.get("GCP_PROJECT_ID")
        self.location = location or os.environ.get("GCP_LOCATION", "us-central1")
        
        # Determine API version
        self.api_version = api_version or os.environ.get("VERTEX_AI_API_VERSION", "v1")
        
        # V2 API (Collections)
        self.collection_id = collection_id or os.environ.get("VERTEX_AI_COLLECTION_ID")
        
        # V1 API (Index/Endpoint) - legacy
        self.index_id = index_id or os.environ.get("VERTEX_AI_INDEX_ID")
        self.index_endpoint_id = index_endpoint_id or os.environ.get(
            "VERTEX_AI_INDEX_ENDPOINT_ID"
        )

        if not self.project:
            raise ValueError("GCP_PROJECT_ID environment variable is required")
        
        # Validate configuration based on API version
        if self.api_version == "v2":
            if not self.collection_id:
                raise ValueError(
                    "collection_id is required for V2 API. "
                    "Set VERTEX_AI_COLLECTION_ID environment variable or provide collection_id parameter"
                )
        else:  # V1
            if not self.index_id or not self.index_endpoint_id:
                raise ValueError(
                    "index_id and index_endpoint_id are required for V1 API. "
                    "Set VERTEX_AI_INDEX_ID and VERTEX_AI_INDEX_ENDPOINT_ID environment variables"
                )

        aiplatform.init(project=self.project, location=self.location)

        self.embedding_provider = VertexAIEmbeddingProvider(
            model_name=embedding_model, project=self.project, location=self.location
        )
        self.dimensions = 768

        # V1 API clients (lazy-loaded)
        self._index = None
        self._index_client = None
        
        # V2 API client (lazy-loaded)
        self._collection_client = None

    @property
    def index(self):
        """Lazy-load V1 Index (legacy)"""
        if self._index is None and self.index_id and self.api_version == "v1":
            from google.cloud import aiplatform_v1
            self._index_client = aiplatform_v1.IndexServiceClient()
            self._index = self._index_client.get_index(
                name=f"projects/{self.project}/locations/{self.location}/indexes/{self.index_id}"
            )
        return self._index

    @property
    def collection_client(self):
        """Lazy-load V2 Collection client"""
        if self._collection_client is None and self.api_version == "v2":
            from google.cloud import vectorsearch_v1beta
            self._collection_client = vectorsearch_v1beta.VectorSearchServiceClient()
        return self._collection_client

    def add(self, ids: list[str], documents: list[str], metadatas: list[dict]) -> None:
        """Add documents to the vector store (V1 or V2)"""
        if self.api_version == "v2":
            self._add_v2(ids, documents, metadatas)
        else:
            self._add_v1(ids, documents, metadatas)

    def _add_v1(self, ids: list[str], documents: list[str], metadatas: list[dict]) -> None:
        """Add documents using V1 Index API (legacy)"""
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
                restricts=metadatas[i] if metadatas[i] else {},
            )
            datapoints.append(datapoint)

        self.index.upsert_datapoints(datapoints=datapoints)

    def _add_v2(self, ids: list[str], documents: list[str], metadatas: list[dict]) -> None:
        """Add documents using V2 Collection API (upsert: create or update)"""
        from google.cloud import vectorsearch_v1beta
        from google.api_core import exceptions

        embeddings = self.get_embeddings(documents)

        collection_name = f"projects/{self.project}/locations/{self.location}/collections/{self.collection_id}"
        
        # Use DataObjectServiceClient for creating/updating individual data objects
        data_object_client = vectorsearch_v1beta.DataObjectServiceClient()
        
        # Create or update each Data Object individually
        for i, doc_id in enumerate(ids):
            # Merge metadata with document content
            data = metadatas[i].copy() if metadatas[i] else {}
            data["page_content"] = documents[i]
            
            # Sanitize data: remove None values and convert to strings
            sanitized_data = {}
            for key, value in data.items():
                if value is None:
                    continue  # Skip None values
                elif isinstance(value, (str, int, float, bool)):
                    sanitized_data[key] = value
                elif isinstance(value, (list, dict)):
                    # Convert complex types to JSON strings
                    import json
                    sanitized_data[key] = json.dumps(value)
                else:
                    # Convert other types to string
                    sanitized_data[key] = str(value)
            
            # Create Data Object (ID is specified in request, not in DataObject constructor)
            data_object = vectorsearch_v1beta.DataObject(
                data=sanitized_data,
                vectors={"embedding": {"dense": {"values": embeddings[i]}}},
            )
            
            try:
                # Try to create the data object
                request = vectorsearch_v1beta.CreateDataObjectRequest(
                    parent=collection_name,
                    data_object_id=doc_id,
                    data_object=data_object,
                )
                data_object_client.create_data_object(request=request)
            except exceptions.AlreadyExists:
                # If it already exists, update it instead
                data_object.name = f"{collection_name}/dataObjects/{doc_id}"
                update_request = vectorsearch_v1beta.UpdateDataObjectRequest(
                    data_object=data_object,
                )
                data_object_client.update_data_object(request=update_request)

    def delete(self, ids: list[str]) -> None:
        """Delete documents from the vector store (V1 or V2)"""
        if self.api_version == "v2":
            self._delete_v2(ids)
        else:
            self._delete_v1(ids)

    def _delete_v1(self, ids: list[str]) -> None:
        """Delete documents using V1 Index API (legacy)"""
        if not self.index:
            raise RuntimeError(
                "No index configured. Set VERTEX_AI_INDEX_ID environment variable or provide index_id"
            )

        self.index.remove_datapoints(datapoint_ids=ids)

    def _delete_v2(self, ids: list[str]) -> None:
        """Delete documents using V2 Collection API"""
        from google.cloud import vectorsearch_v1beta

        collection_name = f"projects/{self.project}/locations/{self.location}/collections/{self.collection_id}"
        request = vectorsearch_v1beta.DeleteDataObjectsRequest(
            collection=collection_name,
            data_object_ids=ids,
        )
        
        self.collection_client.delete_data_objects(request=request)

    def query(self, query_texts: list[str], n_results: int = 5, filter_dict: dict = None) -> dict:
        """Query the vector store (V1 or V2)"""
        if self.api_version == "v2":
            return self._query_v2(query_texts, n_results, filter_dict)
        else:
            return self._query_v1(query_texts, n_results)

    def _query_v1(self, query_texts: list[str], n_results: int = 5) -> dict:
        """Query using V1 Index/Endpoint API (legacy)"""
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

    def _query_v2(self, query_texts: list[str], n_results: int = 5, filter_dict: dict = None) -> dict:
        """Query using V2 Collection API"""
        from google.cloud import vectorsearch_v1beta

        query_embedding = self.get_embeddings(query_texts)[0]

        collection_name = f"projects/{self.project}/locations/{self.location}/collections/{self.collection_id}"
        
        # Build vector search request for V2
        vector_search = vectorsearch_v1beta.VectorSearch(
            search_field="embedding",  # Our vector field name
            vector={"values": query_embedding},
            top_k=n_results,
        )
        
        # Add filter if provided (V2 uses dict-based filtering)
        if filter_dict:
            vector_search.filter = filter_dict

        request = vectorsearch_v1beta.SearchDataObjectsRequest(
            parent=collection_name,
            vector_search=vector_search,
        )

        # Use DataObjectSearchServiceClient for V2 search
        search_client = vectorsearch_v1beta.DataObjectSearchServiceClient()
        response = search_client.search_data_objects(request=request)

        # Parse response
        ids = []
        distances = []
        documents = []
        metadatas = []

        if response.results:
            for result in response.results:
                # Extract ID from name
                ids.append(result.data_object.name.split("/")[-1])
                
                # Extract distance
                distances.append(result.distance if hasattr(result, 'distance') else 0.0)
                
                # Extract document content and metadata
                if result.data_object.data:
                    data = dict(result.data_object.data)
                    doc_content = data.pop("page_content", "")
                    documents.append(doc_content)
                    metadatas.append(data)
                else:
                    # No data in result - use empty values
                    documents.append("")
                    metadatas.append({})

        results = {
            "ids": [ids],
            "distances": [distances],
            "documents": [documents],
            "metadatas": [metadatas],
        }

        return results

    def _get_index_endpoint_name(self):
        """Get V1 Index Endpoint name (legacy)"""
        return f"projects/{self.project}/locations/{self.location}/indexEndpoints/{self.index_endpoint_id}"

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return self.embedding_provider.embed(texts)

    def close(self) -> None:
        pass
