#!/bin/bash
# LegacyLens - Startup Script
# Starts all services from the project root

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo "  LegacyLens - Starting Services"
echo "========================================="

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo "Error: docker-compose.yml not found in $SCRIPT_DIR"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Please edit $SCRIPT_DIR/.env and add your OPENAI_API_KEY"
        exit 1
    else
        echo "Error: .env.example not found either"
        exit 1
    fi
fi

# Check if codebase is cloned
if [ ! -d "codebase/gnucobol" ]; then
    echo "Cloning GnuCOBOL codebase..."
    git clone --depth 1 https://github.com/OCamlPro/gnucobol.git codebase/gnucobol
fi

echo ""
echo "Starting Docker Compose from: $SCRIPT_DIR"
echo "  App (UI + API): http://localhost:8000"
echo "  Health:         http://localhost:8000/api/health"
echo "  API Docs:       http://localhost:8000/docs"
echo ""

docker-compose up --build
