# LegacyLens — RAG Architecture Document

## Vector Database Selection

**Chosen: Qdrant (self-hosted via Docker)**

### Why Qdrant
- Fast Rust-based implementation with low-latency cosine similarity search
- Excellent metadata filtering (filter by file path, language, chunk type, division)
- Simple REST API — easy to integrate with FastAPI backend
- No external cost — self-hosted via Docker for $0 infra on MVP
- Payload indexes for fast filtered queries across 1,700+ chunks

### Tradeoffs Considered
| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Qdrant | Fast, free self-hosted, great filtering | No built-in hybrid search, self-managed | **Selected** |
| Pinecone | Managed, easy setup, free tier | Vendor lock-in, limited free tier | Rejected |
| ChromaDB | Simple API, embedded mode | Less production-ready, limited filtering | Rejected |
| Weaviate | Hybrid search built-in | Heavier setup, GraphQL complexity | Rejected |

---

## Embedding Strategy

**Model: OpenAI text-embedding-3-small (1536 dimensions)**

### Why This Model
- Good cost/quality tradeoff at ~$0.02 per 1M tokens
- 1536 dimensions provides sufficient semantic resolution for code
- Handles code reasonably well despite being a general-purpose model
- Large context training — captures meaning across code structures

### Embedding Stats
- Total chunks: **1,788**
- Total tokens: **1,361,493**
- Estimated embedding cost: **~$0.03** per full ingestion
- Batch size: 100 chunks per API call with async processing

### Future Consideration
- Voyage Code 2 (code-specific, same 1536 dim) for improved code understanding

---

## Chunking Approach

Legacy COBOL code requires structural awareness. We use a **tiered chunking strategy**:

### 1. COBOL Files — Paragraph-Level Chunking (Primary)
- Detects DIVISION boundaries (IDENTIFICATION, ENVIRONMENT, DATA, PROCEDURE)
- Detects SECTION boundaries (WORKING-STORAGE, FILE, etc.)
- Detects PARAGRAPH boundaries within PROCEDURE DIVISION
- Each structural element becomes one chunk
- **Result: 7 division chunks, 11 section chunks** from COBOL files

### 2. C Files — Function-Level Chunking
- Regex-based function signature detection
- Brace-depth tracking to find function boundaries
- Handles both same-line and next-line opening braces
- **Result: 26 function chunks** detected from C source files

### 3. Fixed-Size Fallback
- For content that doesn't match structural patterns
- 800 tokens per chunk (optimal for 1536-dim embeddings)
- 150-token overlap (~15%) to preserve context across boundaries
- **Result: 1,744 fixed-size chunks** as fallback

### Metadata Preserved Per Chunk
```
file_path, start_line, end_line, chunk_type, name,
division, section, language, dependencies, tokens, content_hash
```

### Boundary Detection Patterns
- COBOL divisions: `^\s*(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION`
- COBOL sections: `^\s*([A-Z][A-Z0-9\-]*)\s+SECTION\s*\.`
- COBOL paragraphs: `^(\s{0,3}[A-Z][A-Z0-9\-]*)\s*\.\s*$`
- Dependencies: PERFORM, CALL, COPY references extracted per chunk

---

## Retrieval Pipeline

### Query Flow
1. **Query embedding** — Same model (text-embedding-3-small) for consistency
2. **Qdrant search** — Top-k cosine similarity with optional metadata filters
3. **Ambiguity detection** — If top result score < 0.5, expand from k=5 to k=8
4. **Context assembly** — Merge adjacent chunks from same file, respect 8K token budget
5. **Answer generation** — GPT-4o with structured prompt and citation enforcement

### Re-ranking
- Cosine distance scores used as primary ranking
- Adjacent chunk merging for better context coherence
- Deduplication by file_path + start_line

### Context Assembly
- Retrieved chunks sorted by relevance score
- Adjacent chunks from same file merged to avoid fragmentation
- Total context capped at ≤8K tokens to stay within LLM context budget
- Each chunk formatted with header: `File: path | Lines: X-Y | Type: name`

### Query Expansion
- Dynamic k adjustment: low-confidence results trigger expanded search
- Metadata filtering available: by language, file path, chunk type

---

## Failure Modes

### When Retrieval Finds Nothing
- Return: "No relevant code found. Try rephrasing your query."
- Expand search to k=10 as fallback

### Ambiguous Queries
- Detect low similarity threshold (< 0.5)
- Expand to k=8 for broader results
- Future: Ask clarifying follow-up questions

### Known Edge Cases
- Very large C functions (>1200 tokens) get split into fixed-size sub-chunks, losing some function-level context
- COBOL fixed-format column handling may miss some edge cases in non-standard files
- Config files (.conf) always use fixed-size chunking — no structural awareness

### Rate Limiting
- Exponential backoff retry (3 attempts) on OpenAI API calls
- Batch embedding (100 chunks/call) to minimize API calls

---

## Performance Results

| Metric | Target | Actual |
|--------|--------|--------|
| Codebase coverage | 100% files indexed | **100%** (68/68 files) |
| Total chunks | — | **1,788** |
| Avg tokens/chunk | ~800 | **761** |
| Embedding cost | — | **~$0.03** per ingestion |
| Query latency | <3 seconds | <3s (retrieval <500ms + LLM <2s) |
| Retrieval precision | >70% top-5 | Measured via test queries |
| Ingestion throughput | 10K+ LOC in <5 min | **132K LOC** chunked in seconds |

### Codebase Statistics
- **68 files** processed (37 C, 10 COBOL, 21 config)
- **132,166 lines** of code indexed
- **1,361,493 tokens** embedded
- Languages: C (95.5% of LOC), COBOL (1.4%), Config (3.1%)
