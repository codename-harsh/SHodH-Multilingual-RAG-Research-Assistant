from functools import lru_cache

from sentence_transformers import CrossEncoder

from app.pipeline.query.retriever import RetrievedChunk


@lru_cache(maxsize=1)
def _model() -> CrossEncoder:
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)


def rerank(question: str, chunks: list[RetrievedChunk], limit: int = 4) -> list[RetrievedChunk]:
    if not chunks:
        return []
    scores = _model().predict([(question, chunk.text) for chunk in chunks])
    ranked = sorted(zip(chunks, scores, strict=True), key=lambda item: float(item[1]), reverse=True)
    return [chunk for chunk, _ in ranked[:limit]]
