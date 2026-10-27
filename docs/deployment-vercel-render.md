# Public demo deployment: Vercel + Render

Shodh runs as separate services. Vercel hosts the Next.js interface. Render hosts FastAPI, the Celery worker, PostgreSQL, and Redis-compatible Key Value. Qdrant Cloud stores vectors, and an S3-compatible bucket stores PDFs shared between the API and worker.

This is a controlled demo deployment. `SHODH_API_KEY` is a shared access gate, not user accounts or tenant isolation. Do not upload private documents. A public multi-user launch still needs real authentication, per-user document ownership, rate limiting, and operational monitoring.

## 1. Rotate the provider credentials

The Cohere and Gemini keys previously pasted into the chat should be revoked in their provider consoles. Create replacement keys there and enter them only in Render's secret prompts. Never commit them or put them in `NEXT_PUBLIC_*` variables.

## 2. Push the reviewed deployment branch to GitHub

From PowerShell at the repository root:

```powershell
git status --short
git add .env.example README.md render.yaml docs/deployment-vercel-render.md `
  backend/Dockerfile backend/app backend/tests/test_config.py backend/tests/test_upload_storage.py `
  backend/poetry.lock backend/pyproject.toml backend/entrypoint.sh `
  docker-compose.yml frontend/app/chat/page.tsx frontend/.dockerignore
git commit -m "Prepare Shodh for hosted deployment"
git push -u origin codex/shodh-audit
```

Open a pull request from `codex/shodh-audit` into `main` and merge it after CI passes. The Render Blueprint and Vercel project must use the merged `main` branch.

## 3. Create the Vercel project

1. In Vercel, import `codename-harsh/SHodH-Multilingual-RAG-Research-Assistant` from GitHub.
2. Set **Root Directory** to `frontend`; leave the Next.js framework preset and build command at their detected defaults.
3. Add these Production environment variables:

   - `NEXT_PUBLIC_API_URL`: temporary value `https://example.invalid` until Render creates the API URL.
   - `NEXT_PUBLIC_REQUIRE_API_KEY`: `true`.

4. Deploy once and copy the assigned `*.vercel.app` production URL. This first frontend deploy will not be able to call the API yet.

## 4. Create external data services

1. Create a Qdrant Cloud cluster in Singapore. Copy its HTTPS cluster URL and API key.
2. Create an S3-compatible bucket in Singapore (Cloudflare R2 works). Create an access key limited to that bucket. Note its bucket name and S3 endpoint, usually `https://<account-id>.r2.cloudflarestorage.com`; use region `auto` for R2.

## 5. Create Render services from the Blueprint

1. In Render, choose **New → Blueprint** and select this repository's merged `main` branch.
2. Review the `render.yaml` resources: PostgreSQL, private Key Value, API web service, and Celery worker. These managed services have paid compute/storage charges; select the sizes shown in the Blueprint or larger if required by workload.
3. When prompted, enter the rotated Cohere and Gemini keys; Qdrant URL and key; the new Shodh shared demo key; the Vercel production origin for `CORS_ORIGINS` (for example `https://your-project.vercel.app`); and the bucket name, endpoint, access key, and secret key.
4. Let the API and worker deploy. The API startup runs Alembic migrations. Wait until the API health check is green.
5. Copy the actual public API URL from the Render API service dashboard. Verify `https://<actual-api-host>/health` returns `{"status":"ok",...}` and `/ready` returns HTTP 200 with all three checks `ok`.

## 6. Connect Vercel to the API

In Vercel Project → Settings → Environment Variables, replace `NEXT_PUBLIC_API_URL` with the actual Render API URL (no trailing slash). Keep `NEXT_PUBLIC_REQUIRE_API_KEY=true`, then redeploy Production so the API URL is compiled into the frontend.

Open the Vercel site, enter the shared demo key, upload a small PDF, wait for ingestion to complete, then ask a question and verify citations. Do not share the demo key publicly; everyone with that key shares the same document corpus.

## Local validation commands

Run these from the repository root in PowerShell after deployment:

```powershell
Invoke-RestMethod https://<actual-api-host>/health
Invoke-RestMethod https://<actual-api-host>/ready
```

For the local stack, keep using `docker compose up -d` and `http://localhost:3000`.
