# Shodh

> **Evidence-first multilingual RAG.**

Shodh is a production-minded research assistant for asking grounded questions over multilingual documents. It combines page-aware ingestion, multilingual dense embeddings, BM25 sparse retrieval, hybrid score fusion, local cross-encoder reranking, citation-constrained generation, and RAGAS evaluation.

The project is intentionally built as a conventional software product rather than a demo-shaped AI wrapper. The backend, worker, vector store, relational store, frontend, and evaluation runner have explicit boundaries and testable interfaces.

## Architecture

```mermaid
flowchart LR
    User --> Next[Next.js 15]
    Next --> API[FastAPI]
    API --> Ingest[/ingest/]
    API --> Query[/query/]
    Ingest --> Redis[(Redis)]
    Redis --> Worker[Celery Worker]
    Worker --> PDF[PyMuPDF]
    Worker --> Split[512-token / 128-overlap splitter]
    Worker --> Cohere[Cohere multilingual embeddings]
    Worker --> Qdrant[(Qdrant)]
    Query --> Cohere
    Query --> Qdrant
    Qdrant --> Fuse[Dense + BM25 fusion]
    Fuse --> Rerank[Cross-Encoder]
    Rerank --> Gemini[Gemini]
    API --> PG[(PostgreSQL)]
    Eval[Evaluation / RAGAS] --> API
```

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI, Python 3.11 |
| Async jobs | Celery + Redis |
| Relational data | PostgreSQL + SQLAlchemy + Alembic |
| Vector search | Qdrant |
| Dense embeddings | Cohere `embed-multilingual-v3.0` |
| Sparse retrieval | Qdrant BM25 / FastEmbed |
| Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Generation | Gemini, configurable model |
| PDF parsing | PyMuPDF |
| Chunking | LangChain recursive splitter + token counting |
| Evaluation | RAGAS |
| Frontend | Next.js 15, React 19, Tailwind, shadcn-style primitives |
| Charts | Recharts |
| CI | GitHub Actions + GHCR |

## Local setup

Requirements: Docker Desktop / Docker Engine with the Compose plugin, plus enough memory for the API and worker images. The first image build downloads the Python and Node dependencies.

```bash
cp .env.example .env
```

The sample PostgreSQL password is only for a private local development stack. Provider keys are optional for starting the services. The application will report a clear configuration error if you try a provider-backed feature without its key.

Optional backend API-key gate:

```dotenv
SHODH_API_KEY=your_local_key
```

Set `NEXT_PUBLIC_REQUIRE_API_KEY=true` to show the key-entry gate in the UI. Keep `SHODH_API_KEY` only in the backend environment; users enter it in the UI and it is sent in the request header. Never put the secret itself in a `NEXT_PUBLIC_*` variable.

Start the stack:

```bash
docker compose up --build
```

Then:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

`/health` verifies the API process. `/ready` verifies PostgreSQL, Redis, and Qdrant connectivity.

Open `http://localhost:3000` for the application.

The local stack does not need Cohere or Gemini keys to start. PDF ingestion requires `COHERE_API_KEY`; grounded queries require both `COHERE_API_KEY` and `GEMINI_API_KEY`. The first query also downloads the local Cross-Encoder model and therefore needs access to the model host. The checked-in evaluation dataset intentionally contains placeholders, so `/evaluate` reports that it is not runnable until real document IDs, expected answers, and relevant chunk IDs are supplied. No scores are generated from placeholder data.

For PowerShell, create the environment file with `Copy-Item .env.example .env`; on macOS/Linux use `cp .env.example .env`. In both cases the intended startup command is `docker compose up --build` from the repository root.

## Services

| Service | Port | Purpose |
|---|---:|---|
| frontend | 3000 | Research UI |
| backend | 8000 | FastAPI API |
| worker | — | Celery ingestion worker |
| qdrant | 6333 | Dense + sparse vector store |
| postgres | 5432 | Metadata and query traces |
| redis | 6379 | Celery broker/result backend |

The worker is intentionally a separate service. The original five-service shape becomes six runtime containers once asynchronous ingestion is implemented. Combining the API and Celery worker would make local development simpler but production isolation worse.

## API

### `GET /health`

Returns `200` when the API process is alive.

### `POST /ingest`

Multipart upload of a PDF. Returns a job ID immediately.

```json
{
  "job_id": "...",
  "doc_id": "...",
  "status": "queued"
}
```

### `GET /ingest/{job_id}`

Returns the ingestion state and chunk count.

### `GET /documents`

Lists indexed documents.

### `DELETE /documents/{doc_id}`

Deletes document metadata and its Qdrant points.

### `POST /query`

```json
{
  "question": "What is the main finding?",
  "doc_id": "...",
  "language": "en"
}
```

The language filter is optional. The response includes the generated answer, page/chunk citations, detected language, latency, and the retrieved context trace used by evaluation.

### `GET /query_logs`

Returns recent query history.

### `POST /evaluate`

Runs the golden-set evaluation and returns the latest JSON report.

## Ingestion details

- PDFs are parsed page by page.
- Chunks target 512 tokens with 128-token overlap.
- A chunk never crosses a page boundary.
- Cohere embeddings are batched in groups of 96.
- Qdrant stores named `dense` and `sparse` vectors.
- Payload includes `page`, `doc_id`, `chunk_id`, `text`, and detected `language`.

## Query details

The retrieval stage gets 20 dense and 20 BM25 candidates. Each score family is normalized independently, then combined as:

`fused = alpha * dense + (1 - alpha) * sparse`

The default `alpha` is 0.7. The fused top 20 are passed to the local cross-encoder, which keeps the top 4 for generation.

The generation prompt requires:

- context-only answers
- explicit `[page X, chunk Y]` citations
- an explicit statement when the answer is absent
- an answer in the same language as the question

## Evaluation

Starter data lives in `evaluation/golden_dataset/questions.json`.

Replace the 15 sample placeholders with real document IDs, expected answers, and relevant chunk IDs. Then run:

```bash
python evaluation/run_eval.py
```

Reports are written to:

- `evaluation/reports/latest.json`
- `evaluation/reports/latest.html`

The paper in `docs/paper.md` deliberately does not invent scores. Populate its results table from the generated report after running the actual golden set.

## Tests

```bash
make test
```

The ingestion stage includes unit coverage for page boundaries, token limits, and chunk ID scoping. CI additionally builds the frontend and Docker images.

## Production readiness and deployment

The repository is **hackathon / portfolio / internal-demo ready** and is structured for production hardening. It is not an automatically deployed public SaaS yet because that requires your cloud accounts, managed database/vector/Redis instances, provider secrets, domain, and deployment credentials.

Before an external production launch, use managed PostgreSQL, Redis and Qdrant, object storage for uploads, TLS, secret management, rate limiting, centralized logs/metrics, backups, and a real identity provider. The current API-key gate is suitable for a controlled demo, not multi-tenant authentication.

The deployment workflow is designed around:

1. Python tests.
2. Frontend production build.
3. Docker image builds.
4. GHCR publication.
5. A configurable hosted-platform deployment hook.

### Local deployment

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

Open `http://localhost:3000`. To enable the optional key gate, set `SHODH_API_KEY` and `NEXT_PUBLIC_REQUIRE_API_KEY=true` in `.env`, then rebuild the frontend. Provider keys are only needed to run ingestion and generation.

### Public demo: Vercel + Render

The checked-in `render.yaml` describes a Render API, Celery worker, PostgreSQL database, and private Redis-compatible Key Value service. Qdrant Cloud and S3-compatible object storage are external managed services: configure their URLs and credentials in the Render environment group. PDFs use the bucket in hosted mode so the API and worker can run on separate machines. Local Docker Compose continues to use its shared local volume.

Deploy the frontend separately on Vercel by importing this GitHub repository and setting **Root Directory** to `frontend`. Configure `NEXT_PUBLIC_API_URL` with the public Render API URL and `NEXT_PUBLIC_REQUIRE_API_KEY=true` before the production build. Configure the matching API key only on the backend as `SHODH_API_KEY`, and include the Vercel production origin in Render's `CORS_ORIGINS`.

This shared API key is only a controlled-demo gate. It is not user authentication or tenant isolation. Do not put private documents or sensitive data in a public demo. A public multi-user launch still needs real user authentication, per-user document access control, rate limits, backups, and monitoring. The example resource sizes are starting points, not a claim of tested autoscaling capacity. Do not expose PostgreSQL, Redis, or Qdrant to the public internet.

The Render Blueprint asks for provider secrets during setup; keep these in provider dashboards, never in Git or `NEXT_PUBLIC_*` variables. Vercel deploys only the Next.js frontend. The API and worker remain separate long-running services.

See [`docs/deployment-vercel-render.md`](docs/deployment-vercel-render.md) for the ordered setup steps and PowerShell commands.

## Documentation

- `docs/architecture.md` — component and data-flow explanation
- `docs/paper.md` — research paper draft
- `docs/demo-script.md` — two-minute product demo
- `evaluation/README.md` — golden dataset instructions

## License

MIT. See `LICENSE`.
