# LegacyLens

> RAG-powered system for navigating large legacy enterprise codebases through natural language.

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

## Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API key
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### 1. Clone & Setup

```bash
git clone https://github.com/s85191939/LegacyLens.git
cd LegacyLens
```

### 2. Clone the Target Codebase

```bash
git clone --depth 1 https://github.com/OCamlPro/gnucobol.git codebase/gnucobol
```

### 3. Create Environment File

```bash
cp .env.example .env
```

Then open `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### 4. Run with Docker Compose

**Option A — Use the startup script** (recommended, from the main LegacyLens folder):

```bash
cd /path/to/LegacyLens
./start.sh
```

The script checks for `.env` and the codebase, then starts Docker Compose.

**Option B — Run manually:**

```bash
cd /path/to/LegacyLens
docker-compose up --build
```

This starts three services:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard

### 5. Ingest the Codebase

Once all services are running, trigger ingestion of the GnuCOBOL codebase:

```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"reingest": true}'
```

Check ingestion progress:

```bash
curl http://localhost:8000/api/ingest/status
```

### 6. Query the Codebase

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Where is the main entry point of the compiler?"}'
```

Or open http://localhost:3000 in your browser and use the web interface.

## Local Development

### Backend

```bash
cd backend
pip install -r requirements.txt

# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant:latest

# Run backend
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

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
