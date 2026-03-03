#!/usr/bin/env python3
"""Start script for Railway and other PaaS: bind to PORT from environment."""
import os

def main():
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        log_level="info",
    )

if __name__ == "__main__":
    main()
