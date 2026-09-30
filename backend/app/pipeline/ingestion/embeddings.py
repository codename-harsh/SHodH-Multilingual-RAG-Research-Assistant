from collections.abc import Sequence

import cohere

from app.core.config import get_settings


class CohereEmbedder:
    def __init__(self, client=None, settings=None) -> None:
        settings = settings or get_settings()
        self.batch_size = settings.embed_batch_size
        self.model = settings.cohere_embed_model
        if client is None:
            if not settings.cohere_api_key:
                raise ValueError("COHERE_API_KEY is required for document ingestion")
            client = cohere.ClientV2(api_key=settings.cohere_api_key)
        self.client = client

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = list(texts[start : start + self.batch_size])
            response = self.client.embed(
                texts=batch,
                model=self.model,
                input_type="search_document",
                embedding_types=["float"],
            )
            vectors.extend(response.embeddings.float)
        return vectors
