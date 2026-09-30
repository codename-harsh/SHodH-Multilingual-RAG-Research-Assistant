from dataclasses import dataclass
from uuid import UUID

from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient, models

from app.core.config import get_settings


@dataclass
class RetrievedChunk:
    page: int
    chunk_id: str
    doc_id: UUID
    text: str
    score: float


class HybridRetriever:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection = settings.qdrant_collection
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        self.alpha = settings.hybrid_alpha

    def retrieve(self, dense: list[float], question: str, doc_id: UUID | None = None, language: str | None = None, limit: int = 20) -> list[RetrievedChunk]:
        must = []
        if doc_id:
            must.append(models.FieldCondition(key="doc_id", match=models.MatchValue(value=str(doc_id))))
        if language:
            must.append(models.FieldCondition(key="language", match=models.MatchValue(value=language)))
        query_filter = models.Filter(must=must) if must else None

        dense_hits = self.client.query_points(
            collection_name=self.collection,
            query=dense,
            using="dense",
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        ).points

        sparse = next(iter(self.sparse_model.embed([question])))
        sparse_hits = self.client.query_points(
            collection_name=self.collection,
            query=models.SparseVector(indices=sparse.indices.tolist(), values=sparse.values.tolist()),
            using="sparse",
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        ).points

        dense_scores = {str(hit.id): hit.score for hit in dense_hits}
        sparse_scores = {str(hit.id): hit.score for hit in sparse_hits}
        ids = set(dense_scores) | set(sparse_scores)

        def normalize(scores: dict[str, float]) -> dict[str, float]:
            if not scores:
                return {}
            lo, hi = min(scores.values()), max(scores.values())
            if hi == lo:
                return {key: 1.0 for key in scores}
            return {key: (value - lo) / (hi - lo) for key, value in scores.items()}

        dn, sn = normalize(dense_scores), normalize(sparse_scores)
        fused = sorted(ids, key=lambda point_id: self.alpha * dn.get(point_id, 0.0) + (1 - self.alpha) * sn.get(point_id, 0.0), reverse=True)[:limit]
        payload_by_id = {str(hit.id): hit.payload for hit in dense_hits + sparse_hits}

        return [
            RetrievedChunk(
                page=int(payload_by_id[point_id]["page"]),
                chunk_id=str(payload_by_id[point_id]["chunk_id"]),
                doc_id=UUID(str(payload_by_id[point_id]["doc_id"])),
                text=str(payload_by_id[point_id]["text"]),
                score=self.alpha * dn.get(point_id, 0.0) + (1 - self.alpha) * sn.get(point_id, 0.0),
            )
            for point_id in fused
        ]
