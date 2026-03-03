#!/usr/bin/env python3
"""Start script for Railway and other PaaS: bind to PORT from environment."""
import os
import sys

def main():
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting on {host}:{port} (PORT={os.environ.get('PORT', 'not set')})", flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        log_level="info",
    )

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal: {e}", flush=True)
        sys.exit(1)
