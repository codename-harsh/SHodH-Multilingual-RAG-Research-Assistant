# Engineering Decisions

1. **Worker is a separate container.** Async PDF processing belongs outside the request process.
2. **Uploads use a shared local volume for development.** The worker receives a path, not PDF bytes through Redis. A production object-storage adapter can replace this later.
3. **Chunks are page-scoped.** This makes citations deterministic.
4. **Dense and sparse vectors use named Qdrant vector fields.** Retrieval can address each representation independently.
5. **Hybrid fusion uses normalized score families with alpha=0.7.** This avoids treating raw dense and BM25 scores as directly comparable.
6. **The cross-encoder is loaded lazily.** API startup should not block on model initialization.
7. **Provider integrations are isolated.** Cohere and Gemini clients can be replaced or mocked without rewriting pipeline orchestration.
8. **Query traces are persisted.** Evaluation and UI history consume the same evidence trace used during generation.
9. **Alembic owns schema evolution.** Runtime `create_all()` is not used in production.
10. **The visual language is deliberately quiet.** Dense information hierarchy, neutral surfaces, restrained motion, and evidence visibility take precedence over decorative AI-dashboard patterns.
