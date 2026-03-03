# LegacyLens — Setup Guide

## Prerequisites

- **Docker & Docker Compose** — [Install Docker Desktop](https://docs.docker.com/get-docker/)
- **OpenAI API Key** — [Get one here](https://platform.openai.com/api-keys)
- **Git** — For cloning the repository and target codebase
- **Node.js 18+** — Only needed for local frontend development
- **Python 3.9+** — Only needed for local backend development

---

## Quick Start (Docker — Recommended)

### Step 1: Clone the Repository

```bash
git clone https://github.com/s85191939/LegacyLens.git
cd LegacyLens
```

### Step 2: Clone the Target Codebase

```bash
git clone --depth 1 https://github.com/OCamlPro/gnucobol.git codebase/gnucobol
```

### Step 3: Create Environment File

```bash
cp .env.example .env
```

Open `.env` in your editor and add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### Step 4: Start All Services

**Option A — Use the startup script:**

```bash
./start.sh
```

**Option B — Run Docker Compose directly:**

```bash
docker-compose up --build
```

### Step 5: Verify Services Are Running

Everything is on port **8000**:

| What | URL | Expected |
|------|-----|----------|
| UI | http://localhost:8000 | Web UI loads |
| Health | http://localhost:8000/api/health | `{"status": "healthy"}` |
| API Docs | http://localhost:8000/docs | Swagger UI |

### Step 6: Ingest the Codebase

```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"reingest": true}'
```

Monitor progress:

```bash
curl http://localhost:8000/api/ingest/status
```

Expected output when complete:

```json
{
  "running": false,
  "last_stats": {
    "files_scanned": 68,
    "files_processed": 68,
    "total_chunks": 1788,
    "total_tokens": 1361493,
    "total_embeddings": 1788,
    "duration_seconds": 45.2
  }
}
```

### Step 7: Query the Codebase

**Via CLI:**

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Where is the main entry point of the compiler?"}'
```

**Via Web UI:**

Open http://localhost:8000 and type your question.

---

## Local Development (Without Docker)

### Backend

Run all commands from the **project root** (`LegacyLens/`):

```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Start Qdrant separately
docker run -d -p 6333:6333 qdrant/qdrant:latest

# Create .env file with your OPENAI_API_KEY
cp .env.example .env

# Start the backend (must be from project root so "backend" package resolves)
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:3000 and proxies `/api` to backend at port 8000.

---

## Project Structure

```
LegacyLens/
├── start.sh                # One-command startup script
├── docker-compose.yml      # Qdrant + Backend + Frontend
├── Dockerfile.backend      # Python/FastAPI container
├── Dockerfile.frontend     # Node build → Nginx serve
├── nginx.conf              # API proxy + SPA routing
├── .env.example            # Template for environment variables
├── .dockerignore           # Exclude files from Docker builds
│
├── backend/
│   ├── main.py             # FastAPI app entry point
│   ├── config.py           # Pydantic settings
│   ├── requirements.txt    # Python dependencies
│   ├── ingestion/
│   │   ├── scanner.py      # File discovery
│   │   ├── preprocessor.py # Encoding + COBOL format handling
│   │   ├── chunker.py      # Syntax-aware chunking
│   │   └── pipeline.py     # Orchestrates ingestion
│   ├── embeddings/
│   │   └── embedder.py     # OpenAI embedding with batching
│   ├── vectordb/
│   │   └── qdrant_store.py # Qdrant CRUD + search
│   ├── rag/
│   │   ├── retriever.py    # Query → search → context assembly
│   │   └── generator.py    # LLM answer generation
│   └── routers/
│       ├── health.py       # GET /api/health, /api/stats
│       ├── ingest.py       # POST /api/ingest
│       └── query.py        # POST /api/query
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx         # Main app with query interface
│   │   └── components/
│   │       ├── QueryInput.jsx    # Search input
│   │       ├── AnswerPanel.jsx   # LLM answer display
│   │       ├── ResultsPanel.jsx  # Source list
│   │       └── CodeBlock.jsx     # Code viewer
│   ├── package.json
│   └── vite.config.js
│
├── codebase/               # Target codebase (gitignored)
│   └── gnucobol/           # GnuCOBOL source
│
└── docs/                   # Project documentation
    ├── RAG_ARCHITECTURE.md
    ├── AI_COST_ANALYSIS.md
    └── SETUP_GUIDE.md
```

---

## API Reference

### Health & Stats

```
GET /api/health      → { status, qdrant, collection }
GET /api/stats       → { collection: { points_count, status } }
```

### Ingestion

```
POST /api/ingest     → { status, message }
  Body: { "codebase_path": null, "reingest": false }

GET /api/ingest/status → { running, last_stats }
```

### Query

```
POST /api/query      → { query, answer, sources, retrieval_time_ms, total_time_ms }
  Body: {
    "query": "string",
    "top_k": 5,
    "language": null,
    "file_path": null,
    "feature": null,   // "explain" | "dependencies" | "patterns" | "documentation" | "business_logic"
    "stream": false
  }
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `docker-compose.yml not found` | Make sure you're in the LegacyLens root directory |
| `OPENAI_API_KEY not set` | Create `.env` file with your key (see Step 3) |
| Qdrant connection refused | Ensure Qdrant container is running: `docker ps` |
| No results from queries | Run ingestion first: `POST /api/ingest` |
| Slow first query | First query warms up the embedding model — subsequent queries are faster |
