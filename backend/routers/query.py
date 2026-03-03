"""Query endpoint - natural language search and answer generation."""

import time
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import json

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    """Request body for querying the codebase."""
    query: str
    top_k: Optional[int] = None
    language: Optional[str] = None
    file_path: Optional[str] = None
    feature: Optional[str] = None  # "explain", "dependencies", "patterns", "documentation", "business_logic"
    stream: bool = False
    fast_mode: Optional[bool] = None


class SourceInfo(BaseModel):
    """Source code reference."""
    file_path: str
    start_line: int
    end_line: int
    chunk_type: str
    name: str
    language: str
    score: float
    content: str
    dependencies: List[str] = []


class QueryResponse(BaseModel):
    """Response from a query."""
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    retrieval_time_ms: float
    total_time_ms: float
    total_tokens: int


@router.post("/api/query")
async def query_codebase(request: Request, body: QueryRequest):
    """
    Query the codebase with natural language.
    Returns relevant code snippets and an LLM-generated answer.
    Always returns a valid response (answer or reindex message); never leaves the UI empty.
    """
    start_time = time.time()
    safe_fallback = "Something went wrong. Try REINDEX above to reindex the codebase, or rephrasing your query."

    try:
        # Check if Qdrant is connected
        if not getattr(request.app.state, "qdrant_connected", False):
            raise HTTPException(
                status_code=503,
                detail="Qdrant vector database is not connected. Please check QDRANT_URL and QDRANT_API_KEY settings.",
            )

        retriever = request.app.state.retriever
        generator = request.app.state.generator

        # Fast mode defaults to true for non-streaming API calls
        fast_mode = body.fast_mode if body.fast_mode is not None else (not body.stream)

        # 1. Retrieve relevant chunks (with fallbacks so we rarely have 0 when index has data)
        retrieval_result = await retriever.retrieve(
            query=body.query,
            top_k=body.top_k,
            language=body.language,
            file_path=body.file_path,
        )

        if not retrieval_result.sources:
            total_ms = (time.time() - start_time) * 1000
            # Detect empty index so we never show a generic "no results" when the real issue is no index
            store = request.app.state.store
            index_empty = False
            try:
                info = await store.get_collection_info()
                points = info.get("points_count")
                if points is None:
                    points = info.get("vectors_count")
                if points is None or (isinstance(points, (int, float)) and points == 0):
                    index_empty = True
            except Exception:
                # Collection may not exist yet (e.g. fresh deploy)
                index_empty = True

            if index_empty:
                no_results_answer = "No code indexed yet. Click REINDEX above to ingest the codebase, then try your query again."
            else:
                no_results_answer = "No relevant code found. Try rephrasing your query or broadening the search."

            if body.stream:
                async def empty_stream():
                    yield json.dumps({
                        "type": "sources",
                        "sources": [],
                        "retrieval_time_ms": retrieval_result.retrieval_time_ms,
                        "index_empty": index_empty,
                    }) + "\n"
                    yield json.dumps({
                        "type": "answer_chunk",
                        "content": no_results_answer,
                    }) + "\n"
                    yield json.dumps({
                        "type": "done",
                        "total_time_ms": total_ms,
                    }) + "\n"

                return StreamingResponse(
                    empty_stream(),
                    media_type="application/x-ndjson",
                )

            return QueryResponse(
                query=body.query,
                answer=no_results_answer,
                sources=[],
                retrieval_time_ms=retrieval_result.retrieval_time_ms,
                total_time_ms=total_ms,
                total_tokens=0,
            )

        # 2. Generate answer
        if body.stream:
            async def stream_response():
                yield json.dumps({
                    "type": "sources",
                    "sources": retrieval_result.sources,
                    "retrieval_time_ms": retrieval_result.retrieval_time_ms,
                }) + "\n"

                answer_gen = await generator.generate_answer(
                    query=body.query,
                    context=retrieval_result.context,
                    sources=retrieval_result.sources,
                    feature=body.feature,
                    stream=True,
                )
                async for chunk in answer_gen:
                    yield json.dumps({"type": "answer_chunk", "content": chunk}) + "\n"

                total_ms = (time.time() - start_time) * 1000
                yield json.dumps({
                    "type": "done",
                    "total_time_ms": total_ms,
                }) + "\n"

            return StreamingResponse(
                stream_response(),
                media_type="application/x-ndjson",
            )
        else:
            answer = await generator.generate_answer(
                query=body.query,
                context=retrieval_result.context,
                sources=retrieval_result.sources,
                feature=body.feature,
                stream=False,
                fast_mode=fast_mode,
            )

            total_ms = (time.time() - start_time) * 1000

            return QueryResponse(
                query=body.query,
                answer=answer,
                sources=retrieval_result.sources,
                retrieval_time_ms=retrieval_result.retrieval_time_ms,
                total_time_ms=total_ms,
                total_tokens=retrieval_result.total_tokens,
            )

    except HTTPException:
        raise
    except Exception as exc:
        total_ms = (time.time() - start_time) * 1000
        if body.stream:
            async def error_stream():
                yield json.dumps({"type": "sources", "sources": [], "retrieval_time_ms": 0, "index_empty": False}) + "\n"
                yield json.dumps({"type": "answer_chunk", "content": safe_fallback}) + "\n"
                yield json.dumps({"type": "done", "total_time_ms": total_ms}) + "\n"

            return StreamingResponse(
                error_stream(),
                media_type="application/x-ndjson",
            )
        return QueryResponse(
            query=body.query,
            answer=safe_fallback,
            sources=[],
            retrieval_time_ms=0,
            total_time_ms=total_ms,
            total_tokens=0,
        )
