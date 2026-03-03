"""Query endpoint - natural language search and answer generation."""

import time
from fastapi import APIRouter, Request
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
    """
    start_time = time.time()

    retriever = request.app.state.retriever
    generator = request.app.state.generator

    # 1. Retrieve relevant chunks
    retrieval_result = await retriever.retrieve(
        query=body.query,
        top_k=body.top_k,
        language=body.language,
        file_path=body.file_path,
    )

    if not retrieval_result.sources:
        total_ms = (time.time() - start_time) * 1000
        return QueryResponse(
            query=body.query,
            answer="No relevant code found. Try rephrasing your query or broadening the search.",
            sources=[],
            retrieval_time_ms=retrieval_result.retrieval_time_ms,
            total_time_ms=total_ms,
            total_tokens=0,
        )

    # 2. Generate answer
    if body.stream:
        # Return streaming response
        async def stream_response():
            # First send sources as a JSON line
            yield json.dumps({
                "type": "sources",
                "sources": retrieval_result.sources,
                "retrieval_time_ms": retrieval_result.retrieval_time_ms,
            }) + "\n"

            # Then stream the answer
            answer_gen = await generator.generate_answer(
                query=body.query,
                context=retrieval_result.context,
                sources=retrieval_result.sources,
                feature=body.feature,
                stream=True,
            )
            async for chunk in answer_gen:
                yield json.dumps({"type": "answer_chunk", "content": chunk}) + "\n"

            # Final stats
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
        # Non-streaming response
        answer = await generator.generate_answer(
            query=body.query,
            context=retrieval_result.context,
            sources=retrieval_result.sources,
            feature=body.feature,
            stream=False,
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
