# Backend

Python FastAPI backend for Sobriquets. Provides a REST + SSE API, a LangGraph chat agent, a semantic search engine backed by pgvector, an ingestion pipeline, and a wiki linter.

## Setup

### With Docker (recommended)

From the repo root:

```bash
make up       # starts db + backend + frontend
make migrate  # run Alembic migrations
```

The backend is available at `http://localhost:8000`.

### Without Docker

Requires Python 3.11+ and a running PostgreSQL 16 instance with the `vector` extension enabled.

```bash
cd backend

# Install dependencies (uv preferred, pip also works)
uv venv && source .venv/bin/activate
uv pip install -e .

# or: pip install -e .

# Set environment variables (copy from ../.env.example)
export POSTGRES_HOST=localhost
export POSTGRES_DB=sobriquets
export POSTGRES_USER=sobriquets
export POSTGRES_PASSWORD=sobriquets_dev
export ANTHROPIC_API_KEY=<your key>

# Apply migrations
alembic upgrade head

# Start the server
uvicorn sobriquets.main:app --reload --host 0.0.0.0 --port 8000
```

## API Reference

All endpoints are prefixed with `/api`.

### GET /api/health

Health check. Returns the total number of ingested chunks.

```json
{ "status": "ok", "wiki_chunks": 142 }
```

On database error: `{ "status": "degraded", "wiki_chunks": 0, "error": "..." }`

---

### POST /api/chat

Chat with the LangGraph agent. Returns an SSE stream.

**Request**

```json
{ "message": "What is a qubit?", "session_id": "optional-uuid" }
```

**SSE Event Stream**

```
event: token
data: {"type": "token", "content": "A qubit"}

event: token
data: {"type": "token", "content": " is..."}

event: source
data: {"type": "source", "sources": [{"title": "Qubits", "file_path": "quantum-computing/qubits.md", "heading": "Overview", "relevance_score": 0.91}]}

event: done
data: {"type": "done"}
```

On error: `event: error` with `{"type": "error", "content": "..."}`

The response header `X-Session-Id` contains the session UUID for follow-up messages. Conversation history is held in memory per session.

---

### POST /api/search

Semantic search over wiki chunks.

**Request**

```json
{ "query": "superconducting qubits", "top_k": 5, "topic": "quantum-computing" }
```

`top_k` range: 1–20. `topic` is optional — omit to search all topics.

**Response**

```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "content": "...",
      "heading": "Physical Implementations > Superconducting Qubits",
      "source_title": "Qubits",
      "source_path": "quantum-computing/qubits.md",
      "topic": "quantum-computing",
      "score": 0.91
    }
  ]
}
```

`score` is cosine similarity (0–1, higher is more relevant).

---

### GET /api/topics

List all topics with page counts.

```json
{ "topics": [{ "name": "quantum-computing", "page_count": 4 }] }
```

---

### GET /api/pages/{topic}

List pages within a topic.

```json
{ "pages": [{ "title": "Qubits", "path": "quantum-computing/qubits.md" }] }
```

## Ingestion Pipeline

The ingestion pipeline reads `wiki/pages/`, chunks each markdown file by heading, generates embedding vectors, and upserts into pgvector. Files that have not changed (by SHA-256 hash) are skipped.

```bash
# Via Docker (from repo root)
make ingest              # ingest new/changed pages
make ingest-force        # force re-ingest everything

# Directly
python -m sobriquets.ingest                    # incremental
python -m sobriquets.ingest --topic <slug>     # one topic only
python -m sobriquets.ingest --force            # ignore hashes
python -m sobriquets.ingest --dry-run          # preview without writing
```

Chunking strategy: each H2/H3 section becomes one chunk. Chunks smaller than 100 characters are merged with the next section. Chunks larger than ~4000 characters are split at paragraph boundaries. The heading hierarchy is preserved in chunk metadata for search context.

## Wiki Linter

Checks the wiki for structural issues.

```bash
make lint-wiki
# or directly:
python -m sobriquets.lint
```

Checks performed:
- Missing or incomplete front-matter (`title`, `topic` required)
- Orphan pages (pages not referenced by any other page)
- Broken cross-references (`[[pages/...]]` links pointing to non-existent files)
- Stale source references (sources listed in front-matter that no longer exist)

## Running Tests

```bash
make test
# or directly (from backend/):
pytest
```

106 tests covering: markdown chunker, SHA-256 hasher, ingestion pipeline, LangGraph agent tools, FastAPI endpoints, wiki linter. No database or external services required — all I/O is mocked.

## Module Structure

```
sobriquets/
  main.py          # FastAPI app, lifespan (init DB + embeddings), CORS
  config.py        # Pydantic BaseSettings — all env vars
  api/
    routes.py      # /api/health, /api/chat, /api/search, /api/topics, /api/pages
  agent/
    graph.py       # LangGraph StateGraph definition
    tools.py       # search_knowledge_base, list_wiki_pages, get_wiki_page
    prompts.py     # System prompt
  db/
    models.py      # WikiSource, WikiChunk SQLAlchemy models
    session.py     # Async engine + session factory
    repository.py  # semantic_search, list_topics, list_pages_by_topic, ...
  embeddings/
    provider.py    # Abstract base + factory function
    sentence_transformers.py  # Local embedding (lazy-loaded)
    openai_compat.py          # OpenAI-compatible API embedding
  ingest/
    __main__.py    # CLI entry point
    pipeline.py    # scan -> filter -> parse -> chunk -> embed -> upsert
    chunker.py     # Heading-based markdown splitter
    hasher.py      # SHA-256 file hashing
  lint/
    __main__.py    # CLI entry point
    checks.py      # Lint check functions
```
