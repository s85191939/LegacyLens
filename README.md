# LegacyLens

> RAG-powered system for navigating large legacy enterprise codebases through natural language.

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
   Or: `docker-compose up --build`

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

## Overview

LegacyLens makes the **GnuCOBOL** compiler codebase (~128K LOC, 432 files) queryable through natural language. It uses syntax-aware chunking, vector embeddings, and LLM-powered answer generation to help developers understand unfamiliar legacy code.

## Architecture

| Component | Technology |
|-----------|-----------|
| Vector DB | Qdrant (self-hosted Docker) |
| Embeddings | OpenAI text-embedding-3-small (1536 dim) |
| LLM | GPT-4o |
| Chunking | COBOL paragraph-level + C function-level + fixed-size fallback |
| Backend | FastAPI (Python) |
| Frontend | React + Vite + Tailwind CSS |
| Deployment | Docker Compose |

## Deploy on Railway

1. **New project** → Deploy from GitHub repo, use existing `Dockerfile` and `railway.json`.
2. **Variables** (Railway dashboard → your service → Variables):
   - `OPENAI_API_KEY` (required) — your OpenAI key.
   - `QDRANT_URL` (optional) — e.g. `https://xxx.qdrant.io` if using [Qdrant Cloud](https://cloud.qdrant.io/).
   - `QDRANT_API_KEY` (optional) — required if using Qdrant Cloud.
3. **PORT** is set by Railway; the app binds to it automatically.
4. Without Qdrant the app runs in **degraded** mode (UI and health work; ingest/query need Qdrant). Add a Qdrant Cloud instance and set the variables above to enable full RAG.
5. Health check: Railway uses `/api/health` (or `/health`). The app binds to `PORT` and starts within a few seconds; Qdrant connection is tried with a short timeout so the deploy does not hang.

**If you see "Application failed to respond":** Open the service **Deploy logs** in Railway. Confirm the log line `Starting on 0.0.0.0:<port>` appears and that no Python traceback follows. Set `OPENAI_API_KEY` in Variables (required). The app responds with HTTP 200 even when Qdrant is unavailable (degraded mode).

## Quick Start

**Prerequisites:** Docker & Docker Compose, OpenAI API key.

See **[Instructions (Docker — one port)](#instructions-docker--one-port)** above for the full step-by-step. In short: clone repo and codebase, set `OPENAI_API_KEY` in `.env`, run `./start.sh`, then open http://localhost:8000. Use http://localhost:8000/api/health to verify. Ingest once with `POST /api/ingest`, then query via the UI or `POST /api/query`.

## Local Development

Run all commands from the **project root** (`LegacyLens/`), not from `backend/` or `frontend/`.

### Backend

```bash
# From project root (LegacyLens/)
pip install -r backend/requirements.txt

# In another terminal: start Qdrant
docker run -p 6333:6333 qdrant/qdrant:latest

# Run backend (must be from project root so "backend" package is found)
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
# From project root
cd frontend
npm install
npm run dev
```

Frontend dev server runs at http://localhost:3000 and proxies `/api` to the backend at http://localhost:8000.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check + Qdrant status |
| GET | `/api/stats` | Collection statistics |
| POST | `/api/ingest` | Trigger codebase ingestion |
| GET | `/api/ingest/status` | Check ingestion progress |
| POST | `/api/query` | Natural language query |

## Code Understanding Features

- **Code Explanation** - Plain English explanation of functions/sections
- **Dependency Mapping** - PERFORM/CALL/COPY analysis
- **Pattern Detection** - Find similar code patterns across the codebase
- **Documentation Gen** - Generate documentation for undocumented code
- **Business Logic Extract** - Identify and explain business rules

## Performance Targets

| Metric | Target |
|--------|--------|
| Query latency | <3 seconds end-to-end |
| Retrieval precision | >70% relevant chunks in top-5 |
| Codebase coverage | 100% of files indexed |
| Ingestion throughput | 10,000+ LOC in <5 minutes |

## Chunking Strategy

1. **COBOL files**: Paragraph-level chunking (DIVISION/SECTION/PARAGRAPH boundaries)
2. **C files**: Function-level chunking
3. **Fallback**: Fixed-size (800 tokens) with 15% overlap

Each chunk preserves metadata: file path, line numbers, function/paragraph name, division, section, dependencies.
