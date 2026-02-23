import os
from typing import Any

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from vector_store.base import VectorStoreProvider, EmbeddingProvider


class OpenRouterEmbedder(EmbeddingFunction):
    def __init__(
        self,
        api_key: str,
        model: str = "google/gemini-embedding-001",
        batch_size: int = 64,
        timeout: int = 60,
        max_chars: int | None = None,
    ):
        import requests

        self.api_key = api_key
        self.model = model
        self.batch_size = batch_size
        self.timeout = timeout
        self.max_chars = max_chars
        self.base_url = "https://openrouter.ai/api/v1/embeddings"
        self._requests = requests

    def _sanitize(self, x) -> str:
        if x is None:
            return ""
        if not isinstance(x, str):
            x = str(x)
        if self.max_chars is not None and len(x) > self.max_chars:
            x = x[: self.max_chars]
        return x

    def _post(self, batch: list[str]) -> list[list[float]]:
        payload = {"model": self.model, "input": batch}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/chroma-core/chroma",
            "X-Title": "ChromaDB Local Client",
        }
        r = self._requests.post(
            self.base_url, headers=headers, json=payload, timeout=self.timeout
        )

        try:
            data = r.json()
        except Exception:
            raise RuntimeError(
                f"Non-JSON response (status {r.status_code}): {r.text[:300]}"
            )

        if r.status_code != 200 or "error" in data:
            err = data.get("error", {})
            raise RuntimeError(
                f"OpenRouter Error {err.get('code', r.status_code)}: {err.get('message')}"
            )

        if "data" not in data:
            raise RuntimeError(f"Unexpected response format: {data}")

        return [item["embedding"] for item in data["data"]]

    def _embed_with_bisect(
        self, batch: list[str], start_index: int
    ) -> list[list[float]]:
        try:
            return self._post(batch)
        except Exception as e:
            if len(batch) == 1:
                preview = batch[0][:200].replace("\n", "\\n")
                raise RuntimeError(
                    f"Embedding failed for item index {start_index}. "
                    f"First 200 chars: {preview!r}. Underlying error: {e}"
                ) from e

            mid = len(batch) // 2
            left = self._embed_with_bisect(batch[:mid], start_index)
            right = self._embed_with_bisect(batch[mid:], start_index + mid)
            return left + right

    def __call__(self, input: Documents) -> Embeddings:
        if not input:
            return []

        docs = [self._sanitize(x) for x in list(input)]

        out: list[list[float]] = []
        i = 0
        while i < len(docs):
            batch = docs[i : i + self.batch_size]
            out.extend(self._embed_with_bisect(batch, i))
            i += self.batch_size

        return out


class ChromaDBProvider(VectorStoreProvider):
    def __init__(self, collection_name: str = "courses", persist_dir: str = None):
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")

        embedder = OpenRouterEmbedder(
            api_key=api_key,
            model="google/gemini-embedding-001",
        )

        if persist_dir:
            self.client = chromadb.PersistentClient(path=persist_dir)
        else:
            self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(
            name=collection_name, embedding_function=embedder
        )

        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name, embedding_function=embedder
        )

    def add(self, ids: list[str], documents: list[str], metadatas: list[dict]) -> None:
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    def delete(self, ids: list[str]) -> None:
        self.collection.delete(ids=ids)

    def query(self, query_texts: list[str], n_results: int = 5) -> dict:
        return self.collection.query(query_texts=query_texts, n_results=n_results)

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return self.collection._embedding_function(texts)

    def close(self) -> None:
        pass
