from collections.abc import Sequence

import cohere

from app.core.config import get_settings


class CohereEmbedder:
    def __init__(self) -> None:
        settings = get_settings()
        self.batch_size = settings.embed_batch_size
        self.model = settings.cohere_embed_model
        self.client = cohere.ClientV2(api_key=settings.cohere_api_key)

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
