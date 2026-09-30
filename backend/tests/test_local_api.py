from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.models.document import Document
from app.models.ingestion_job import IngestionJob
from app.models.query_log import QueryLog


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def __iter__(self):
        return iter(self.rows)


class FakeDB:
    def __init__(self):
        self.rows = []
        self.commits = 0
        self.rollbacks = 0

    def add(self, row):
        if isinstance(row, Document):
            if row.n_chunks is None:
                row.n_chunks = 0
            if row.uploaded_at is None:
                row.uploaded_at = datetime.now(timezone.utc)
        if isinstance(row, QueryLog):
            if row.id is None:
                row.id = uuid4()
            if row.created_at is None:
                row.created_at = datetime.now(timezone.utc)
        self.rows.append(row)

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1

    async def get(self, model, key):
        for row in self.rows:
            if isinstance(row, model) and getattr(row, "id", getattr(row, "job_id", None)) == key:
                return row
        return None

    async def execute(self, statement):
        if not getattr(statement, "column_descriptions", None):
            for row in self.rows:
                if isinstance(row, Document):
                    row.status = "failed"
            return SimpleNamespace()
        entity = statement.column_descriptions[0]["entity"]
        return FakeResult([row for row in self.rows if isinstance(row, entity)])


class FakeTask:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def apply_async(self, **kwargs):
        if self.fail:
            raise RuntimeError("broker unavailable")
        self.calls.append(kwargs)


@pytest.fixture
def local_client(tmp_path, monkeypatch):
    from app.api import dependencies, ingest
    from app.db.session import get_db
    from app.main import app

    state = SimpleNamespace(db=FakeDB(), task=FakeTask(), upload_dir=tmp_path)
    monkeypatch.setattr(ingest, "UPLOAD_DIR", tmp_path)
    app.dependency_overrides[get_db] = lambda: state.db
    app.dependency_overrides[dependencies.get_ingestion_task] = lambda: state.task
    try:
        with TestClient(app) as client:
            yield client, state
    finally:
        app.dependency_overrides.clear()


def test_health_endpoint_works_without_service_credentials(local_client):
    client, _ = local_client

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ready_checks_postgres_redis_and_qdrant(monkeypatch):
    from app import main

    class Connection:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

        async def execute(self, statement):
            assert str(statement) == "SELECT 1"

    class Engine:
        def connect(self):
            return Connection()

    class RedisClient:
        async def ping(self):
            return True

        async def aclose(self):
            return None

    class Qdrant:
        def get_collections(self):
            return SimpleNamespace(collections=[])

        def close(self):
            return None

    monkeypatch.setattr(main, "engine", Engine())
    monkeypatch.setattr(main.Redis, "from_url", lambda url, **kwargs: RedisClient())
    monkeypatch.setattr(main, "QdrantClient", lambda **kwargs: Qdrant())

    response = await main.ready()

    assert response.status_code == 200
    assert response.body == b'{"status":"ready","checks":{"postgres":"ok","redis":"ok","qdrant":"ok"}}'


@pytest.mark.asyncio
async def test_ready_returns_unavailable_if_a_dependency_is_down(monkeypatch):
    from app import main

    class FailedConnection:
        async def __aenter__(self):
            raise OSError("database down")

        async def __aexit__(self, *_):
            return None

    class Engine:
        def connect(self):
            return FailedConnection()

    class RedisClient:
        async def ping(self):
            raise OSError("redis down")

        async def aclose(self):
            return None

    class Qdrant:
        def get_collections(self):
            raise OSError("qdrant down")

        def close(self):
            return None

    monkeypatch.setattr(main, "engine", Engine())
    monkeypatch.setattr(main.Redis, "from_url", lambda url, **kwargs: RedisClient())
    monkeypatch.setattr(main, "QdrantClient", lambda **kwargs: Qdrant())

    response = await main.ready()

    assert response.status_code == 503
    assert b'"status":"degraded"' in response.body


def test_pdf_upload_dispatches_async_job_and_status_can_be_polled(local_client):
    client, state = local_client
    document_bytes = b"%PDF-1.7\nlocal test document"

    response = client.post(
        "/ingest",
        files={"file": ("research.pdf", document_bytes, "application/pdf")},
    )

    assert response.status_code == 202
    accepted = response.json()
    assert accepted["status"] == "queued"
    assert len(state.task.calls) == 1
    assert state.task.calls[0]["task_id"] == accepted["job_id"]
    assert state.task.calls[0]["args"][1] == "research.pdf"
    assert state.db.commits == 1

    job = IngestionJob(job_id=accepted["job_id"], doc_id=accepted["doc_id"])
    state.db.add(job)
    document = None
    for row in state.db.rows:
        if isinstance(row, Document):
            document = row
            break
    assert document is not None

    from app.api import dependencies

    from app.main import app

    app.dependency_overrides[dependencies.get_ingestion_result_factory] = lambda: (
        lambda job_id: SimpleNamespace(failed=lambda: False, result=None)
    )
    try:
        status = client.get(f"/ingest/{accepted['job_id']}")
    finally:
        app.dependency_overrides.pop(dependencies.get_ingestion_result_factory, None)

    assert status.status_code == 200
    assert status.json()["doc_id"] == accepted["doc_id"]
    assert status.json()["status"] == "queued"


def test_document_listing_returns_uploaded_metadata(local_client):
    client, _ = local_client
    client.post("/ingest", files={"file": ("paper.pdf", b"%PDF-1.7\n", "application/pdf")})

    response = client.get("/documents")

    assert response.status_code == 200
    assert response.json()[0]["filename"] == "paper.pdf"
    assert response.json()[0]["status"] == "queued"


def test_invalid_pdf_is_rejected_and_not_queued(local_client):
    client, state = local_client

    response = client.post("/ingest", files={"file": ("not-pdf.pdf", b"not a PDF", "application/pdf")})

    assert response.status_code == 415
    assert state.task.calls == []
    assert state.db.rows == []


def test_upload_reports_queue_outage_and_removes_temporary_file(local_client):
    client, state = local_client
    state.task.fail = True

    response = client.post("/ingest", files={"file": ("paper.pdf", b"%PDF-1.7\n", "application/pdf")})

    assert response.status_code == 503
    assert "queue is unavailable" in response.json()["detail"]
    assert all(row.status == "failed" for row in state.db.rows if isinstance(row, Document))
    assert list(state.upload_dir.glob("*.pdf")) == []


def test_upload_size_limit_is_checked_while_streaming(local_client, monkeypatch):
    from app.api import ingest

    client, state = local_client
    monkeypatch.setattr(ingest, "settings", SimpleNamespace(max_upload_mb=0))

    response = client.post("/ingest", files={"file": ("large.pdf", b"%PDF-1.7", "application/pdf")})

    assert response.status_code == 413
    assert state.task.calls == []
    assert list(state.upload_dir.glob("*.pdf")) == []


def test_multilingual_query_uses_injected_components_and_logs_retrieved_context(local_client):
    from app.api import dependencies
    from app.main import app

    client, state = local_client
    doc_id = uuid4()
    first = SimpleNamespace(page=1, chunk_id="p1-c0", doc_id=doc_id, text="Contexto inicial", score=0.4)
    selected = SimpleNamespace(page=2, chunk_id="p2-c0", doc_id=doc_id, text="La conclusión es clara.", score=0.9)
    calls = {}

    class Embedder:
        def embed(self, question):
            calls["question"] = question
            return [0.1, 0.2]

    class Retriever:
        def retrieve(self, dense, question, filter_doc, language, limit):
            calls["retrieval"] = (dense, question, filter_doc, language, limit)
            return [first, selected]

    class Generator:
        model = "fake-gemini"

        def generate(self, question, context, language):
            calls["generation"] = (question, context, language)
            return "La conclusión está respaldada [page 2, chunk p2-c0]."

    def fake_reranker(question, chunks, limit):
        calls["rerank"] = (question, chunks, limit)
        return [selected]

    app.dependency_overrides.update({
        dependencies.get_query_embedder: lambda: Embedder(),
        dependencies.get_hybrid_retriever: lambda: Retriever(),
        dependencies.get_gemini_generator: lambda: Generator(),
        dependencies.get_chunk_reranker: lambda: fake_reranker,
    })
    try:
        response = client.post(
            "/query",
            json={"question": "¿Cuál es la conclusión principal del estudio?", "doc_id": str(doc_id)},
        )
    finally:
        for dependency in (
            dependencies.get_query_embedder,
            dependencies.get_hybrid_retriever,
            dependencies.get_gemini_generator,
            dependencies.get_chunk_reranker,
        ):
            app.dependency_overrides.pop(dependency, None)

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["detected_language"] == "es"
    assert result["citations"] == [{"page": 2, "chunk_id": "p2-c0", "text_snippet": "La conclusión es clara."}]
    assert result["retrieved_context"] == [{"page": 2, "chunk_id": "p2-c0", "text": "La conclusión es clara."}]
    assert calls["generation"][2] == "es"
    assert calls["retrieval"][2] == doc_id
    assert calls["retrieval"][4] == 20
    query_log = next(row for row in state.db.rows if isinstance(row, QueryLog))
    assert query_log.final_answer == result["answer"]
    assert len(query_log.retrieved_chunks) == 2
    assert state.db.commits == 1

    history = client.get("/query_logs")
    assert history.status_code == 200
    assert history.json()[0]["question"] == "¿Cuál es la conclusión principal del estudio?"
    assert history.json()[0]["answer"] == result["answer"]


def test_query_without_cohere_key_returns_clear_service_unavailable(local_client, monkeypatch):
    from app.pipeline.query import embeddings

    client, _ = local_client
    monkeypatch.setattr(
        embeddings,
        "get_settings",
        lambda: SimpleNamespace(cohere_api_key="", cohere_embed_model="test"),
    )

    response = client.post("/query", json={"question": "What does the paper conclude?"})

    assert response.status_code == 503
    assert "COHERE_API_KEY" in response.json()["detail"]
