# Unified Dockerfile for Railway deployment
# Builds frontend + backend into a single image

# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Production backend + static frontend
FROM python:3.11-slim
WORKDIR /app

# Install git (needed to clone codebase for ingestion)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ backend/

# Copy built frontend into /app/static (served by FastAPI)
COPY --from=frontend-build /app/dist static/

# Clone the GnuCOBOL codebase for ingestion
RUN git clone --depth 1 https://github.com/OCamlPro/gnucobol.git codebase/gnucobol || \
    mkdir -p codebase/gnucobol

EXPOSE 8000

# Railway provides PORT env var; default to 8000 for local
CMD sh -c "python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"
