# LegacyLens

> RAG-powered system for navigating large legacy enterprise codebases through natural language.
https://legacylens-production-9547.up.railway.app/

## MVP Status (Based on Week 3 + Pre-Search Docs)

Current status against core MVP requirements:

- ✅ Ingest at least one legacy codebase (GnuCOBOL)
- ✅ Natural language query interface (web UI + API)
- ✅ Vector retrieval with citations (file + line references in sources)
- ✅ End-to-end RAG flow (embed -> retrieve -> generate)
- ✅ Public deployment path (Railway config included)
- ⚠️ Public deploy health depends on valid Railway env values (`OPENAI_API_KEY`, `QDRANT_URL`, optional `QDRANT_API_KEY`)

Validation tooling added:

- Backend tests: `python3 -m pytest -q backend/tests`
- Basic eval runner (latency + source count + answer presence): `python3 evals/run_eval.py`

If your Railway URL returns 502, the most common cause is environment value formatting or connectivity (especially Qdrant), not missing app code.

---

## Instructions (Docker — one port)

Everything runs on **port 8000**: UI, API, and health check.

1. **Clone and enter the repo**
   ```bash
   git clone https://github.com/s85191939/LegacyLens.git
   cd LegacyLens
   ```

2. **Clone the target codebase**
   ```bash
   git clone --depth 1 https://github.com/OCamlPro/gnucobol.git codebase/gnucobol
   ```

3. **Create `.env` and set your OpenAI API key**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set `OPENAI_API_KEY=sk-your-key`.

4. **Start the app**
   ```bash
   ./start.sh
   ```
   Or: `docker compose up --build`

5. **Verify**
   - **UI**: http://localhost:8000
   - **Health**: http://localhost:8000/api/health
   - **API docs**: http://localhost:8000/docs

6. **Ingest the codebase** (once the app is up)
   ```bash
   curl -X POST http://localhost:8000/api/ingest -H "Content-Type: application/json" -d '{"reingest": true}'
   curl http://localhost:8000/api/ingest/status
   ```

7. **Query** in the browser at http://localhost:8000 or via API (see **Example questions** below).

---

## How to Use LegacyLens (Local + Web)

### Local (recommended)

```bash
git clone https://github.com/s85191939/LegacyLens.git
cd LegacyLens
git clone --depth 1 https://github.com/OCamlPro/gnucobol.git codebase/gnucobol
cp .env.example .env
# set OPENAI_API_KEY in .env
./start.sh
```

Use:

- App UI: `http://localhost:8000`
- Health: `http://localhost:8000/api/health`
- Ingest: `POST http://localhost:8000/api/ingest` body `{"reingest": true}`
- Query: UI or `POST http://localhost:8000/api/query`

### Web (Railway)

1. Open your deployed URL (example): `https://legacylens-production-fecf.up.railway.app/`
2. Verify backend first: `https://.../api/health`
3. If health returns JSON, run ingestion:
   - `POST https://.../api/ingest` body `{"reingest": true}`
4. Query through the web UI.

Note: `degraded` means app is running but Qdrant is unavailable.

---

## Deploy on Railway

1. **New project** -> Deploy from GitHub repo, use existing `Dockerfile` and `railway.json`.
2. **Variables** (Railway dashboard -> your service -> Variables):
   - `OPENAI_API_KEY` (required)
   - `QDRANT_URL` (optional unless you need full RAG; e.g. `https://xxx.qdrant.io`)
   - `QDRANT_API_KEY` (optional; only if your Qdrant requires auth)
   - `QDRANT_COLLECTION` (default `legacylens`)
3. **PORT** is set by Railway; app binds automatically.
4. Without Qdrant the app runs in **degraded** mode (UI + health work; ingest/query disabled).

### Railway Quick Fix Checklist (ASAP)

1. Redeploy latest `main`.
2. Re-save `OPENAI_API_KEY`.
3. Re-save `QDRANT_URL` as a clean URL (no quotes/trailing spaces).
4. If Qdrant does **not** require auth: remove `QDRANT_API_KEY`.
5. If Qdrant **does** require auth: paste `QDRANT_API_KEY` as a single-line token.
6. Confirm `GET /api/health` on Railway returns JSON (not 502).

---

## Example questions

Try these in the UI or via `POST /api/query`:

1. Where is the main entry point of the compiler?
2. How does COBOL file I/O work?
3. What error handling patterns are used?
4. Show me the parser implementation.
5. How are COBOL divisions and sections parsed?
6. Where is symbol table or name resolution handled?
7. How does the code generator emit output?
8. What data structures represent the AST or parse tree?
9. How are COPY and REPLACING directives processed?
10. Where is numeric or decimal arithmetic implemented?

---

## Architecture

| Component | Technology |
|-----------|-----------|
| Vector DB | Qdrant |
| Embeddings | OpenAI text-embedding-3-small (1536 dim) |
| LLM | GPT-4o |
| Chunking | COBOL paragraph-level + C function-level + fixed-size fallback |
| Backend | FastAPI (Python) |
| Frontend | React + Vite + Tailwind CSS |
| Deployment | Docker Compose / Railway |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check + Qdrant status |
| GET | `/health` | Health alias (Railway-friendly) |
| GET | `/api/stats` | Collection statistics |
| POST | `/api/ingest` | Trigger codebase ingestion |
| GET | `/api/ingest/status` | Check ingestion progress |
| POST | `/api/query` | Natural language query |

## Local Development (Without Docker)

Run all commands from project root (`LegacyLens/`).

### Backend

```bash
pip install -r backend/requirements.txt
docker run -d -p 6333:6333 qdrant/qdrant:latest
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server runs at http://localhost:3000 and proxies `/api` to backend at port 8000.
