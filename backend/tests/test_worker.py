from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.pipeline.ingestion.chunker import Chunk, PageText
from app.pipeline.ingestion.embeddings import CohereEmbedder
from app.models.document import Document
from app.workers import ingestion


class FakeDocument:
    def __init__(self, doc_id):
        self.id = doc_id
        self.status = "queued"
        self.n_chunks = 0


class FakeSession:
    def __init__(self, document):
        self.document = document

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def get(self, model, doc_id):
        return self.document if model is Document and doc_id == self.document.id else None

    async def commit(self):
        return None


class FakeStore:
    def __init__(self):
        self.dense_size = None
        self.upserted = None

    def ensure_collection(self, dense_size):
        self.dense_size = dense_size

    def upsert(self, doc_id, chunks, vectors):
        self.upserted = (doc_id, list(chunks), list(vectors))


def _fake_session_factory(document):
    return lambda: FakeSession(document)


@pytest.mark.asyncio
async def test_ingestion_worker_runs_pipeline_and_cleans_upload(tmp_path, monkeypatch):
    doc_id = uuid4()
    document = FakeDocument(doc_id)
    upload = tmp_path / "document.pdf"
    upload.write_bytes(b"fake PDF bytes")
    store = FakeStore()
    chunks = [Chunk(page=1, chunk_id="p1-c0", text="texto"), Chunk(page=2, chunk_id="p2-c0", text="more")]

    class FakeEmbedder:
        def embed(self, texts):
            assert texts == ["texto", "more"]
            return [[0.1, 0.2], [0.3, 0.4]]

    monkeypatch.setattr(ingestion, "SessionLocal", _fake_session_factory(document))
    monkeypatch.setattr(ingestion, "extract_pdf_pages", lambda path: [PageText(1, "texto"), PageText(2, "more")])
    monkeypatch.setattr(ingestion, "chunk_pages", lambda pages: chunks)
    monkeypatch.setattr(ingestion, "CohereEmbedder", FakeEmbedder)
    monkeypatch.setattr(ingestion, "QdrantDocumentStore", lambda: store)

    result = await ingestion._run_ingestion(doc_id, "document.pdf", str(upload))

    assert result == 2
    assert document.status == "complete"
    assert document.n_chunks == 2
    assert store.dense_size == 2
    assert store.upserted[0] == doc_id
    assert store.upserted[1] == chunks
    assert not upload.exists()


@pytest.mark.asyncio
async def test_missing_cohere_key_marks_job_failed_and_removes_upload(tmp_path, monkeypatch):
    doc_id = uuid4()
    document = FakeDocument(doc_id)
    upload = tmp_path / "document.pdf"
    upload.write_bytes(b"fake PDF bytes")

    monkeypatch.setattr(ingestion, "SessionLocal", _fake_session_factory(document))
    monkeypatch.setattr(ingestion, "extract_pdf_pages", lambda path: [PageText(1, "texto")])
    monkeypatch.setattr(ingestion, "chunk_pages", lambda pages: [Chunk(1, "p1-c0", "texto")])
    monkeypatch.setattr(
        ingestion,
        "CohereEmbedder",
        lambda: CohereEmbedder(settings=SimpleNamespace(embed_batch_size=8, cohere_embed_model="test", cohere_api_key="")),
    )

    with pytest.raises(ValueError, match="COHERE_API_KEY"):
        await ingestion._run_ingestion(doc_id, "document.pdf", str(upload))

    assert document.status == "failed"
    assert not upload.exists()


def test_celery_application_registers_ingestion_task():
    from app.workers.celery_app import celery_app

    celery_app.loader.import_default_modules()

    assert "shodh.ingest_document" in celery_app.tasks
