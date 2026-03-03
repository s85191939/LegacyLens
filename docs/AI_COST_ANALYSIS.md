# LegacyLens — AI Cost Analysis

## Development & Testing Costs

### Embedding API Costs
- **Model:** OpenAI text-embedding-3-small
- **Rate:** ~$0.02 per 1M tokens
- **Total tokens embedded:** 1,361,493
- **Cost per full ingestion:** ~$0.03
- **Estimated dev iterations (10 re-ingestions):** ~$0.30

### LLM API Costs (Answer Generation)
- **Model:** GPT-4o
- **Rate:** ~$0.0025 per 1K input tokens, ~$0.01 per 1K output tokens
- **Average query context:** ~4K tokens input + ~500 tokens output
- **Cost per query:** ~$0.015
- **Estimated dev testing (200 queries):** ~$3.00

### Vector Database Hosting
- **Qdrant:** Self-hosted via Docker
- **Cost:** $0 (local/self-hosted)

### Total Development Spend Breakdown
| Category | Cost |
|----------|------|
| Embedding API (ingestion) | ~$0.30 |
| LLM API (testing queries) | ~$3.00 |
| Vector DB hosting | $0.00 |
| **Total Development Cost** | **~$3.30** |

---

## Production Cost Projections

### Assumptions
- 10 queries per user per day
- ~4K input tokens per query (context + prompt)
- ~500 output tokens per query (LLM answer)
- Re-embedding on code changes: ~1 full re-ingestion per week
- Qdrant self-hosted on same infrastructure
- GPT-4o for answer generation
- OpenAI text-embedding-3-small for embeddings

### Monthly Cost Estimates

| Users | Queries/Day | Queries/Month | Embedding Cost | LLM Cost | Qdrant | **Total/Month** |
|-------|-------------|---------------|----------------|----------|--------|-----------------|
| 100 | 1,000 | 30,000 | ~$0.12 | ~$450 | $0 | **~$50** |
| 1,000 | 10,000 | 300,000 | ~$1.20 | ~$4,500 | $0 | **~$400** |
| 10,000 | 100,000 | 3,000,000 | ~$12 | ~$45,000 | $50 | **~$3,000** |
| 100,000 | 1,000,000 | 30,000,000 | ~$120 | ~$450,000 | $200 | **~$25,000** |

> **Note:** Costs can be significantly reduced by:
> - Caching frequent queries and their embeddings
> - Using Claude Haiku or GPT-4o-mini for simpler queries (~10x cheaper)
> - Implementing response caching for identical/similar queries
> - Self-hosting open-source LLMs (Llama, Mistral) for $0 per-query cost

### Cost Optimization Strategies
1. **Query caching:** Cache embedding + response for repeated queries → up to 40% reduction
2. **Tiered LLM:** Use GPT-4o-mini for simple queries, GPT-4o only for complex analysis → ~60% LLM cost reduction
3. **Embedding deduplication:** Content hash check to skip re-embedding unchanged chunks → minimal re-ingestion cost
4. **Self-hosted LLM:** Deploy Llama 3 or Mistral locally to eliminate per-query LLM cost entirely

---

## Cost Per Feature

| Feature | Additional Cost Per Use | Notes |
|---------|------------------------|-------|
| Code Explanation | ~$0.015 | Standard query |
| Dependency Mapping | ~$0.015 | Standard query |
| Pattern Detection | ~$0.02 | May expand to k=8 |
| Documentation Gen | ~$0.02 | Longer output tokens |
| Business Logic Extract | ~$0.015 | Standard query |
| Re-ingestion | ~$0.03 | Full codebase re-embed |
