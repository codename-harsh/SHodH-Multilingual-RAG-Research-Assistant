from collections.abc import Sequence
from uuid import UUID, NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, SparseVectorParams, VectorParams
from fastembed import SparseTextEmbedding
from langdetect import detect, LangDetectException

from app.core.config import get_settings
from app.pipeline.ingestion.chunker import Chunk


class QdrantDocumentStore:
    def __init__(self, client=None, sparse_model=None, settings=None) -> None:
        settings = settings or get_settings()
        self.client = client if client is not None else QdrantClient(url=settings.qdrant_url)
        self.collection = settings.qdrant_collection
        self.sparse_model = (
            sparse_model if sparse_model is not None else SparseTextEmbedding(model_name="Qdrant/bm25")
        )

    def ensure_collection(self, dense_size: int) -> None:
        if self.client.collection_exists(self.collection):
            return
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config={"dense": VectorParams(size=dense_size, distance=Distance.COSINE)},
            sparse_vectors_config={"sparse": SparseVectorParams(index=models.SparseIndexParams(on_disk=False))},
        )

    def upsert(self, doc_id: UUID, chunks: Sequence[Chunk], dense_vectors: Sequence[Sequence[float]]) -> None:
        sparse_vectors = list(self.sparse_model.embed([chunk.text for chunk in chunks]))
        points: list[models.PointStruct] = []
        for chunk, dense, sparse in zip(chunks, dense_vectors, sparse_vectors, strict=True):
            point_id = str(uuid5(NAMESPACE_URL, f"shodh:{doc_id}:{chunk.chunk_id}"))
            try:
                language = detect(chunk.text)
            except LangDetectException:
                language = "unknown"
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector={
                        "dense": list(dense),
                        "sparse": models.SparseVector(indices=sparse.indices.tolist(), values=sparse.values.tolist()),
                    },
                    payload={
                        "page": chunk.page,
                        "doc_id": str(doc_id),
                        "chunk_id": chunk.chunk_id,
                        "text": chunk.text,
                        "language": language,
                    },
                )
            )
        self.client.upsert(collection_name=self.collection, points=points, wait=True)
