#!/usr/bin/env python3
"""Simple eval runner for LegacyLens MVP quality checks."""

import json
import sys
import time
from pathlib import Path

import requests

API = "http://localhost:8000"
MAX_LATENCY_MS = 5000
MIN_SOURCES = 1


def load_queries():
    return json.loads(Path("evals/queries.json").read_text())


def run_query(q):
    t0 = time.time()
    res = requests.post(
        f"{API}/api/query",
        json={"query": q, "stream": False},
        timeout=30,
    )
    elapsed = (time.time() - t0) * 1000
    return res.status_code, res.json(), elapsed


def main():
    queries = load_queries()

    health = requests.get(f"{API}/api/health", timeout=10).json()
    print("health:", health)

    rows = []
    pass_count = 0

    for q in queries:
        code, body, elapsed = run_query(q)
        answer = (body.get("answer") or "").strip()
        sources = body.get("sources") or []

        passed = (
            code == 200
            and len(answer) > 20
            and len(sources) >= MIN_SOURCES
            and elapsed <= MAX_LATENCY_MS
        )
        if passed:
            pass_count += 1

        rows.append(
            {
                "query": q,
                "status_code": code,
                "elapsed_ms": round(elapsed, 1),
                "answer_len": len(answer),
                "sources": len(sources),
                "passed": passed,
            }
        )

    report = {
        "passed": pass_count,
        "total": len(rows),
        "pass_rate": round(pass_count / len(rows), 3) if rows else 0,
        "rows": rows,
    }

    print(json.dumps(report, indent=2))
    Path("evals/latest_report.json").write_text(json.dumps(report, indent=2))

    if pass_count < len(rows):
        sys.exit(1)


if __name__ == "__main__":
    main()
