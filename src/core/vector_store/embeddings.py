"""Shared embedding utilities for vector store providers."""

from __future__ import annotations

from typing import List

from chromadb import Documents, EmbeddingFunction, Embeddings


class OpenRouterEmbedder(EmbeddingFunction):
    def __init__(
        self,
        api_key: str,
        model: str = "google/gemini-embedding-001",
        batch_size: int = 64,
        timeout: int = 60,
        max_chars: int | None = None,
    ) -> None:
        import requests

        self.api_key = api_key
        self.model = model
        self.batch_size = batch_size
        self.timeout = timeout
        self.max_chars = max_chars
        self.base_url = "https://openrouter.ai/api/v1/embeddings"
        self._requests = requests

    def _sanitize(self, value: str | None) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            value = str(value)
        if self.max_chars is not None and len(value) > self.max_chars:
            value = value[: self.max_chars]
        return value

    def _post(self, batch: list[str]) -> list[list[float]]:
        payload = {"model": self.model, "input": batch}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/chroma-core/chroma",
            "X-Title": "ChromaDB Local Client",
        }
        response = self._requests.post(
            self.base_url, headers=headers, json=payload, timeout=self.timeout
        )

        try:
            data = response.json()
        except Exception as exc:  # pragma: no cover - network/parsing guard
            raise RuntimeError(
                f"Non-JSON response (status {response.status_code}): {response.text[:300]}"
            ) from exc

        if response.status_code != 200 or "error" in data:
            error = data.get("error", {})
            message = error.get("message") or data
            raise RuntimeError(
                f"OpenRouter Error {error.get('code', response.status_code)}: {message}"
            )

        if "data" not in data:
            raise RuntimeError(f"Unexpected response format: {data}")

        return [item["embedding"] for item in data["data"]]

    def _embed_with_bisect(self, batch: list[str], start_index: int) -> list[list[float]]:
        try:
            return self._post(batch)
        except Exception as exc:  # pragma: no cover - external service guard
            if len(batch) == 1:
                preview = batch[0][:200].replace("\n", "\\n")
                raise RuntimeError(
                    f"Embedding failed for item index {start_index}. First 200 chars: {preview!r}."
                ) from exc

            midpoint = len(batch) // 2
            left = self._embed_with_bisect(batch[:midpoint], start_index)
            right = self._embed_with_bisect(batch[midpoint:], start_index + midpoint)
            return left + right

    def __call__(self, input_texts: Documents) -> Embeddings:
        if not input_texts:
            return []

        docs = [self._sanitize(value) for value in list(input_texts)]
        output: list[list[float]] = []
        idx = 0
        while idx < len(docs):
            batch = docs[idx : idx + self.batch_size]
            output.extend(self._embed_with_bisect(batch, idx))
            idx += self.batch_size
        return output


def embed_texts(embedder: OpenRouterEmbedder, texts: List[str]) -> list[list[float]]:
    return embedder(texts)
