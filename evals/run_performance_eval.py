#!/usr/bin/env python3
"""Explicit performance-target evaluator for LegacyLens MVP."""

import argparse
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import requests

DEFAULT_TARGETS = {
    "query_latency_ms_p95": 3000,
    "retrieval_precision_top5": 0.70,
    "codebase_coverage": 1.00,
    "ingestion_max_seconds": 300,
    "ingestion_min_lines": 10000,
    "answer_accuracy": 1.00,
}


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    idx = (len(values) - 1) * (p / 100.0)
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return values[lo]
    w = idx - lo
    return values[lo] * (1 - w) + values[hi] * w


def load_queries(path: Path) -> List[Dict[str, Any]]:
    return json.loads(path.read_text())


def ensure_health(api_base: str) -> Dict[str, Any]:
    res = requests.get(f"{api_base}/api/health", timeout=10)
    res.raise_for_status()
    return res.json()


def post_query(api_base: str, query: str, fast_mode: bool = True) -> Dict[str, Any]:
    t0 = time.time()
    res = requests.post(
        f"{api_base}/api/query",
        json={"query": query, "top_k": 5, "stream": False, "fast_mode": fast_mode},
        timeout=60,
    )
    elapsed_ms = (time.time() - t0) * 1000.0
    body = res.json() if res.content else {}
    return {
        "status_code": res.status_code,
        "elapsed_ms": elapsed_ms,
        "body": body,
    }


def source_has_valid_ref(source: Dict[str, Any]) -> bool:
    fp = str(source.get("file_path") or "").strip()
    start = source.get("start_line")
    end = source.get("end_line")
    return bool(fp) and isinstance(start, int) and isinstance(end, int) and start > 0 and end >= start


def source_is_relevant(source: Dict[str, Any], hints: List[str]) -> bool:
    blob = " ".join(
        [
            str(source.get("file_path") or ""),
            str(source.get("name") or ""),
            str(source.get("content") or ""),
            " ".join(source.get("dependencies") or []),
        ]
    ).lower()
    return any(h.lower() in blob for h in hints)


def maybe_reingest(api_base: str, timeout_sec: int) -> Dict[str, Any]:
    req = requests.post(
        f"{api_base}/api/ingest",
        json={"reingest": True},
        timeout=30,
    )
    req.raise_for_status()

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        status = requests.get(f"{api_base}/api/ingest/status", timeout=15).json()
        if not status.get("running"):
            return status
        time.sleep(3)

    raise TimeoutError("Timed out waiting for ingestion to finish")


def fetch_ingest_status(api_base: str) -> Dict[str, Any]:
    res = requests.get(f"{api_base}/api/ingest/status", timeout=15)
    res.raise_for_status()
    return res.json()


def evaluate(api_base: str, query_file: Path, do_reingest: bool, reingest_timeout: int, fast_mode: bool) -> Dict[str, Any]:
    health = ensure_health(api_base)

    if do_reingest:
        ingest_status = maybe_reingest(api_base, reingest_timeout)
    else:
        ingest_status = fetch_ingest_status(api_base)

    last_stats = ingest_status.get("last_stats") or {}
    files_scanned = float(last_stats.get("files_scanned") or 0)
    files_processed = float(last_stats.get("files_processed") or 0)
    total_lines = float(last_stats.get("total_lines") or 0)
    ingest_seconds = float(last_stats.get("duration_seconds") or 0)

    coverage = (files_processed / files_scanned) if files_scanned > 0 else 0.0

    query_defs = load_queries(query_file)
    rows = []
    latencies = []
    relevant_chunks = 0
    total_chunks = 0
    citation_passes = 0

    for item in query_defs:
        q = item["query"]
        hints = item.get("expected_hints") or []
        result = post_query(api_base, q, fast_mode=fast_mode)
        body = result["body"]
        sources = body.get("sources") or []
        answer = str(body.get("answer") or "").strip()
        total_ms = float(body.get("total_time_ms") or result["elapsed_ms"])

        latencies.append(total_ms)

        query_relevant = sum(1 for s in sources[:5] if source_is_relevant(s, hints))
        relevant_chunks += query_relevant
        total_chunks += min(5, len(sources))

        has_valid_citations = bool(sources) and all(source_has_valid_ref(s) for s in sources[: min(5, len(sources))])
        answer_ok = len(answer) > 20
        citation_ok = has_valid_citations and answer_ok
        if citation_ok:
            citation_passes += 1

        rows.append(
            {
                "query": q,
                "status_code": result["status_code"],
                "latency_ms": round(total_ms, 2),
                "top5_returned": min(5, len(sources)),
                "top5_relevant": query_relevant,
                "citation_ok": citation_ok,
            }
        )

    p95_latency = percentile(sorted(latencies), 95)
    mean_latency = statistics.mean(latencies) if latencies else 0.0
    retrieval_precision = (relevant_chunks / total_chunks) if total_chunks > 0 else 0.0
    answer_accuracy = (citation_passes / len(rows)) if rows else 0.0

    throughput_lines_ok = total_lines >= DEFAULT_TARGETS["ingestion_min_lines"]
    throughput_time_ok = ingest_seconds > 0 and ingest_seconds < DEFAULT_TARGETS["ingestion_max_seconds"]

    gates = {
        "query_latency": p95_latency < DEFAULT_TARGETS["query_latency_ms_p95"],
        "retrieval_precision": retrieval_precision > DEFAULT_TARGETS["retrieval_precision_top5"],
        "codebase_coverage": coverage >= DEFAULT_TARGETS["codebase_coverage"],
        "ingestion_throughput": throughput_lines_ok and throughput_time_ok,
        "answer_accuracy": answer_accuracy >= DEFAULT_TARGETS["answer_accuracy"],
    }

    return {
        "api_base": api_base,
        "health": health,
        "targets": DEFAULT_TARGETS,
        "metrics": {
            "query_latency_ms_p95": round(p95_latency, 2),
            "query_latency_ms_mean": round(mean_latency, 2),
            "retrieval_precision_top5": round(retrieval_precision, 4),
            "codebase_coverage": round(coverage, 4),
            "ingestion_duration_seconds": round(ingest_seconds, 2),
            "ingestion_total_lines": int(total_lines),
            "answer_accuracy": round(answer_accuracy, 4),
        },
        "gates": gates,
        "passed": all(gates.values()),
        "queries": rows,
        "ingest_last_stats": last_stats,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run explicit LegacyLens performance target evaluation")
    parser.add_argument(
        "--api-base",
        default=os.getenv("LEGACYLENS_API", "http://localhost:8000"),
        help="Base API URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--queries",
        default="evals/performance_queries.json",
        help="Path to performance query definitions JSON",
    )
    parser.add_argument(
        "--reingest",
        action="store_true",
        default=True,
        help="Trigger full reindex before evaluation (default: true)",
    )
    parser.add_argument(
        "--no-reingest",
        action="store_true",
        help="Skip reindex and use current ingestion stats",
    )
    parser.add_argument(
        "--fast-mode",
        action="store_true",
        default=True,
        help="Use low-latency fast mode for non-stream query tests (default: true)",
    )
    parser.add_argument(
        "--no-fast-mode",
        action="store_true",
        help="Disable fast mode for strict baseline measurement",
    )
    parser.add_argument(
        "--reingest-timeout",
        type=int,
        default=1800,
        help="Seconds to wait for reindex to finish",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    do_reingest = args.reingest and not args.no_reingest
    fast_mode = args.fast_mode and not args.no_fast_mode

    report = evaluate(
        api_base=args.api_base.rstrip("/"),
        query_file=Path(args.queries),
        do_reingest=do_reingest,
        reingest_timeout=args.reingest_timeout,
        fast_mode=fast_mode,
    )

    out_path = Path("evals/performance_report.json")
    out_path.write_text(json.dumps(report, indent=2))

    print(json.dumps(report, indent=2))
    print(f"\nSaved report: {out_path}")

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
