# Sobriquets

A personal knowledge wiki system following Karpathy's three-layer LLM Wiki pattern. Use the `/research` Claude Code skill to build structured wiki pages from authoritative sources, then chat with your knowledge base through a streaming React frontend backed by a LangGraph agent and pgvector.

## Quick Start

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY at minimum

# 2. Start all services
make up

# 3. Run database migrations
make migrate

# 4. Research your first topic (in Claude Code)
/research quantum computing

# 5. Ingest the wiki pages into the vector database
make ingest

# 6. Open the chat UI
open http://localhost:5173
```

## Prerequisites

- Docker and Docker Compose (v2)
- Claude Code with internet access (for the `/research` skill)
- An Anthropic API key (for the chat agent)

Optional: An OpenAI API key if you prefer OpenAI embeddings over the local default.

## Architecture

```mermaid
flowchart TD
    R["/research skill\n(Claude Code)"] -->|writes| W["wiki/\nraw-sources/ + pages/"]
    W -->|make ingest| I["Ingestion CLI\npython -m sobriquets.ingest"]
    I -->|embed + upsert| DB[("PostgreSQL 16\n+ pgvector")]
    UI["React Chat UI\nlocalhost:5173"] <-->|SSE + JSON| API["FastAPI Backend\nlocalhost:8000"]
    API -->|semantic search| DB
    API -->|LangGraph agent| LLM["Claude Sonnet\n(Anthropic API)"]
```

### Three-Layer Wiki Pattern

| Layer | Location | Mutability |
|-------|----------|------------|
| Raw Sources | `wiki/raw-sources/` | Immutable — never edited after creation |
| Wiki Pages | `wiki/pages/` | Regenerated/updated by `/research` |
| Schema | `wiki/schema.md` + `CLAUDE.md` | Manually maintained |

### Data Flow

1. Run `/research <topic>` in Claude Code — the skill fetches authoritative sources, saves raw snapshots to `wiki/raw-sources/`, and generates structured markdown pages in `wiki/pages/`.
2. Run `make ingest` — the ingestion pipeline scans `wiki/pages/`, chunks each page by heading, generates embedding vectors, and upserts into pgvector. Unchanged files (by SHA-256 hash) are skipped.
3. Open the chat UI and ask questions — the LangGraph agent calls `search_knowledge_base`, retrieves relevant chunks via cosine similarity, and streams a synthesized answer with source citations.

### LangGraph Agent

```
START -> agent_node (LLM call)
              |
         has tool calls?
         /           \
    tool_node        END
    (execute)
         \
          -> back to agent_node
```

Agent tools: `search_knowledge_base`, `list_wiki_pages`, `get_wiki_page`

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Database | PostgreSQL 16 + pgvector (HNSW index) |
| Backend | Python 3.11, FastAPI, SQLAlchemy (async), Alembic |
| Agent | LangGraph, LangChain, Claude Sonnet |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` (local, 384-dim) or OpenAI API |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Streaming | Server-Sent Events (SSE) |

## Project Structure

```
sobriquets/
  CLAUDE.md                  # Project conventions + skill registration
  Makefile                   # Dev workflow targets
  docker-compose.yml         # All services
  .env.example               # Configuration template

  wiki/                      # Knowledge base (git-tracked)
    schema.md                # Wiki structure conventions
    raw-sources/             # Immutable source snapshots
    pages/                   # Generated wiki pages

  skills/research/           # Research skill prompt (legacy location)
  .claude/commands/
    research.md              # /research slash command (active)

  backend/
    sobriquets/
      main.py                # FastAPI app entry point
      config.py              # Settings from environment
      api/routes.py          # REST + SSE endpoints
      agent/                 # LangGraph agent + tools + prompts
      db/                    # SQLAlchemy models, session, repository
      embeddings/            # Embedding provider abstraction
      ingest/                # Ingestion pipeline CLI
      lint/                  # Wiki health checks CLI
    tests/                   # 106 unit and integration tests
    db/init.sql              # pgvector extension setup

  frontend/
    src/
      App.tsx                # Layout (sidebar + chat)
      api/                   # TypeScript types + fetch client
      hooks/                 # useChat (SSE streaming), useSearch
      components/            # ChatWindow, MessageList, MessageBubble,
                             # ChatInput, SourceCitation, Sidebar
```

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check with chunk count |
| POST | `/api/chat` | Chat with agent — returns SSE stream |
| POST | `/api/search` | Semantic search over wiki chunks |
| GET | `/api/topics` | List all topics with page counts |
| GET | `/api/pages/{topic}` | List pages in a topic |

See `backend/README.md` for full request/response schemas.

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Required for chat agent | — |
| `EMBEDDING_PROVIDER` | `sentence_transformers` or `openai` | `sentence_transformers` |
| `EMBEDDING_MODEL` | Model name | `all-MiniLM-L6-v2` |
| `EMBEDDING_DIMENSION` | Vector dimension (must match model) | `384` |
| `AGENT_LLM_MODEL` | LLM model for chat agent | `claude-sonnet-4-20250514` |
| `OPENAI_API_KEY` | Required if using OpenAI embeddings | — |
| `POSTGRES_PASSWORD` | Database password | `sobriquets_dev` |
| `CORS_ORIGINS` | Allowed origins for CORS | `http://localhost:5173` |

Full variable reference: `.env.example`

## Development

```bash
make up            # Start all services (Docker)
make migrate       # Apply database migrations
make ingest        # Ingest new/changed wiki pages
make ingest-force  # Force re-ingest everything
make lint-wiki     # Check wiki health (orphans, broken refs)
make test          # Run 106 backend tests
make logs          # Tail all service logs
make down          # Stop all services

# Run frontend outside Docker
make frontend-dev  # cd frontend && npm run dev
```

## Security

This is a single-user personal tool. There is no authentication. The API binds to localhost only. The `.env` file is gitignored — never commit it. API keys live in `.env` only.

See `CLAUDE.md` for full project conventions and skill usage.
