from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.pipeline.ingestion.chunker import Chunk
from app.pipeline.ingestion.embeddings import CohereEmbedder
from app.pipeline.ingestion.qdrant import QdrantDocumentStore
from app.pipeline.llm.gemini import GeminiGenerator
from app.pipeline.query.embeddings import QueryEmbedder
from app.pipeline.query.retriever import HybridRetriever
from app.pipeline.query.reranker import rerank


class FakeCohere:
    def __init__(self):
        self.calls = []

    def embed(self, **kwargs):
        self.calls.append(kwargs)
        vectors = [[float(index), 1.0] for index, _ in enumerate(kwargs["texts"])]
        return SimpleNamespace(embeddings=SimpleNamespace(float=vectors))


def test_document_embeddings_are_batched_and_use_document_mode():
    client = FakeCohere()
    settings = SimpleNamespace(embed_batch_size=2, cohere_embed_model="test-model")
    embedder = CohereEmbedder(client=client, settings=settings)

    vectors = embedder.embed(["one", "two", "three"])

    assert len(vectors) == 3
    assert [len(call["texts"]) for call in client.calls] == [2, 1]
    assert all(call["input_type"] == "search_document" for call in client.calls)
    assert all(call["model"] == "test-model" for call in client.calls)


def test_query_embedding_uses_query_mode_without_provider_credentials():
    client = FakeCohere()
    settings = SimpleNamespace(cohere_api_key="", cohere_embed_model="test-model")
    embedder = QueryEmbedder(client=client, settings=settings)

    assert embedder.embed("¿Qué evidencia hay?") == [0.0, 1.0]
    assert client.calls[0]["input_type"] == "search_query"


def test_missing_cohere_key_has_actionable_error(monkeypatch):
    from app.pipeline.ingestion import embeddings

    monkeypatch.setattr(
        embeddings,
        "get_settings",
        lambda: SimpleNamespace(embed_batch_size=96, cohere_embed_model="test", cohere_api_key=""),
    )
    try:
        CohereEmbedder()
    except ValueError as exc:
        assert "COHERE_API_KEY" in str(exc)
    else:
        raise AssertionError("missing provider key should not create an SDK client")


def test_gemini_client_is_injected_and_only_context_citations_survive():
    captured = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                text="Evidencia confirmada [page 2, chunk p2-c0]. Outra citação [page 9, chunk p9-c7]."
            )

    client = SimpleNamespace(models=FakeModels())
    generator = GeminiGenerator(client=client, model="fake-gemini")
    chunks = [{"page": 2, "chunk_id": "p2-c0", "text": "evidencia"}]

    answer = generator.generate("¿Qué evidencia hay?", chunks, "es")

    assert answer == "Evidencia confirmada [page 2, chunk p2-c0]. Outra citação ."
    assert captured["model"] == "fake-gemini"
    assert "evidencia" in captured["contents"]
    assert "es" in captured["config"].system_instruction


def test_missing_gemini_key_has_actionable_error(monkeypatch):
    from app.pipeline.llm import gemini

    monkeypatch.setattr(
        gemini,
        "get_settings",
        lambda: SimpleNamespace(gemini_api_key="", gemini_model="test"),
    )
    try:
        GeminiGenerator()
    except ValueError as exc:
        assert "GEMINI_API_KEY" in str(exc)
    else:
        raise AssertionError("missing provider key should not create an SDK client")


def test_api_dependency_reports_missing_provider_credentials_as_503(monkeypatch):
    from fastapi import HTTPException

    from app.api import dependencies
    from app.pipeline.query import embeddings as query_embeddings
    from app.pipeline.llm import gemini

    monkeypatch.setattr(
        query_embeddings,
        "get_settings",
        lambda: SimpleNamespace(cohere_api_key="", cohere_embed_model="test"),
    )
    monkeypatch.setattr(
        gemini,
        "get_settings",
        lambda: SimpleNamespace(gemini_api_key="", gemini_model="test"),
    )

    with pytest.raises(HTTPException) as cohere_error:
        dependencies.get_query_embedder()
    with pytest.raises(HTTPException) as gemini_error:
        dependencies.get_gemini_generator()

    assert cohere_error.value.status_code == 503
    assert "COHERE_API_KEY" in cohere_error.value.detail
    assert gemini_error.value.status_code == 503
    assert "GEMINI_API_KEY" in gemini_error.value.detail


class Array(list):
    def tolist(self):
        return list(self)


class FakeSparse:
    def embed(self, texts):
        assert len(texts) == 1
        return [SimpleNamespace(indices=Array([1]), values=Array([1.0]))]


class FakeQdrant:
    def __init__(self, dense_hits, sparse_hits):
        self.responses = {"dense": dense_hits, "sparse": sparse_hits}
        self.calls = []

    def query_points(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(points=self.responses[kwargs["using"]])


def _hit(point_id, score, page, chunk_id):
    return SimpleNamespace(
        id=point_id,
        score=score,
        payload={
            "page": page,
            "chunk_id": chunk_id,
            "doc_id": str(DOCUMENT_ID),
            "text": f"text-{chunk_id}",
            "language": "es",
        },
    )


DOCUMENT_ID = uuid4()


def test_dense_sparse_retrieval_fuses_independent_rankings():
    client = FakeQdrant(
        dense_hits=[_hit("a", 0.9, 1, "p1-c0"), _hit("b", 0.5, 2, "p2-c0")],
        sparse_hits=[_hit("b", 1.0, 2, "p2-c0"), _hit("c", 0.9, 3, "p3-c0")],
    )
    retriever = HybridRetriever(
        client=client,
        sparse_model=FakeSparse(),
        settings=SimpleNamespace(qdrant_collection="test", hybrid_alpha=0.4),
    )

    results = retriever.retrieve([0.1, 0.2], "pregunta", DOCUMENT_ID, "es", 10)

    assert [item.chunk_id for item in results] == ["p2-c0", "p1-c0", "p3-c0"]
    assert [call["using"] for call in client.calls] == ["dense", "sparse"]
    assert all(call["query_filter"].must[0].key == "doc_id" for call in client.calls)
    assert results[0].doc_id == DOCUMENT_ID


def test_qdrant_ingestion_keeps_stable_document_page_and_chunk_metadata():
    class FakeStoreClient:
        def __init__(self):
            self.created = None
            self.points = None

        def collection_exists(self, collection):
            return False

        def create_collection(self, **kwargs):
            self.created = kwargs

        def upsert(self, **kwargs):
            self.points = kwargs["points"]

    class FakeSparse:
        def embed(self, texts):
            return [SimpleNamespace(indices=Array([index + 1]), values=Array([0.5])) for index, _ in enumerate(texts)]

    client = FakeStoreClient()
    store = QdrantDocumentStore(
        client=client,
        sparse_model=FakeSparse(),
        settings=SimpleNamespace(qdrant_collection="test"),
    )
    chunks = [Chunk(4, "p4-c0", "Este es el primer pasaje de investigación."), Chunk(5, "p5-c0", "Este es otro pasaje de investigación.")]
    vectors = [[0.1, 0.2], [0.3, 0.4]]

    store.ensure_collection(2)
    store.upsert(DOCUMENT_ID, chunks, vectors)

    assert client.created["collection_name"] == "test"
    assert client.created["vectors_config"]["dense"].size == 2
    assert [point.payload["page"] for point in client.points] == [4, 5]
    assert [point.payload["chunk_id"] for point in client.points] == ["p4-c0", "p5-c0"]
    assert all(point.payload["doc_id"] == str(DOCUMENT_ID) for point in client.points)
    assert client.points[0].vector["dense"] == vectors[0]
    assert client.points[0].vector["sparse"].indices == [1]


def test_reranker_uses_injected_cross_encoder_and_preserves_chunk_identity():
    from app.pipeline.query.retriever import RetrievedChunk

    first = RetrievedChunk(1, "p1-c0", DOCUMENT_ID, "first", 0.8)
    second = RetrievedChunk(2, "p2-c0", DOCUMENT_ID, "second", 0.7)

    class FakeCrossEncoder:
        def predict(self, pairs):
            assert pairs == [("question", "first"), ("question", "second")]
            return [0.1, 0.9]

    assert rerank("question", [first, second], limit=1, model=FakeCrossEncoder()) == [second]
