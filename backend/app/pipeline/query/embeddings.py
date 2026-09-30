from collections.abc import Sequence

import cohere

from app.core.config import get_settings


class QueryEmbedder:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = cohere.ClientV2(api_key=settings.cohere_api_key)
        self.model = settings.cohere_embed_model

    def embed(self, question: str) -> list[float]:
        response = self.client.embed(
            texts=[question],
            model=self.model,
            input_type="search_query",
            embedding_types=["float"],
        )
        return response.embeddings.float[0]
