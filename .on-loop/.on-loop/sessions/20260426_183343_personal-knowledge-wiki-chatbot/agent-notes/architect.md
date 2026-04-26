# Specification: Sobriquets -- Personal Knowledge Wiki System

## Summary

Sobriquets is a personal knowledge wiki system following Karpathy's three-layer LLM Wiki pattern (Raw Sources, Wiki, Schema). It combines a Claude Code research skill for generating structured markdown knowledge from authoritative sources, a full-stack chat application (React/FastAPI/LangGraph/pgvector) for querying that knowledge, and an ingestion pipeline that bridges the two. The system lives as a monorepo and runs locally via Docker Compose.

## Requirements

### Functional Requirements

1. **FR-001** Research skill: A Claude Code custom slash command (`/research`) that accepts a topic, retrieves authoritative sources, and produces structured markdown wiki pages following the Karpathy pattern.
2. **FR-002** Wiki page generation: The research skill outputs markdown files organized by entity/concept with front-matter metadata, cross-references, and source attributions.
3. **FR-003** Raw source capture: The research skill stores immutable snapshots of source material (URLs, retrieval timestamps, content hashes) that are never modified after creation.
4. **FR-004** Ingestion CLI: A command-line tool (`python -m sobriquets.ingest` or `make ingest`) that reads markdown files from the wiki directory, chunks them, generates embeddings, and upserts into pgvector.
5. **FR-005** Semantic search API: A FastAPI endpoint that accepts a natural language query and returns ranked wiki chunks via pgvector cosine similarity.
6. **FR-006** Chat API: A FastAPI endpoint that accepts a user message and returns a streamed agent response, powered by a LangGraph agent that can search the knowledge base and synthesize answers.
7. **FR-007** Chat UI: A React TypeScript chatbot interface for sending messages and displaying streamed responses with source citations.
8. **FR-008** Conversation history: The chat UI and API maintain per-session conversation history (in-memory for MVP; no persistent conversation storage required initially).
9. **FR-009** Wiki lint operation: A CLI command that checks wiki health -- finds orphan pages, missing cross-references, contradictions, and stale sources.
10. **FR-010** Configurable embeddings: Support both local sentence-transformers models and OpenAI-compatible embedding APIs, switchable via environment variable.

### Non-Functional Requirements

1. **NFR-001** Startup: `docker compose up` brings the entire stack (DB, API, frontend) to a working state within 60 seconds on a modern laptop.
2. **NFR-002** Search latency: Semantic search endpoint responds in under 500ms at p95 for a knowledge base of up to 10,000 chunks.
3. **NFR-003** Portability: Runs on macOS (Apple Silicon) and Linux x86_64 without modification.
4. **NFR-004** Simplicity: No Kubernetes, no cloud dependencies, no external auth. This is a personal single-user tool.
5. **NFR-005** Offline capability: With local embeddings (sentence-transformers), the system works fully offline except for the research skill (which requires internet).
6. **NFR-006** Incremental ingestion: Re-running ingestion only processes new or modified markdown files (based on content hash comparison).

## Architecture

### System Design

```
+------------------------------------------------------------------+
|                        Sobriquets Monorepo                       |
+------------------------------------------------------------------+
|                                                                  |
|  +--------------------+     +-------------------------------+    |
|  | Claude Code Skill  |     |   wiki/                       |    |
|  | (/research)        |---->|   raw-sources/  (immutable)   |    |
|  |                    |     |   pages/        (generated)    |    |
|  +--------------------+     |   schema.md     (conventions)  |    |
|                             +-------------------------------+    |
|                                        |                         |
|                                        v                         |
|  +--------------------+     +-------------------------------+    |
|  | Ingestion CLI      |---->| PostgreSQL 16 + pgvector      |    |
|  | (python -m ingest) |     |   wiki_chunks (embeddings)    |    |
|  +--------------------+     |   wiki_sources (metadata)     |    |
|                             +---------------+---------------+    |
|                                             |                    |
|                                             v                    |
|  +--------------------+     +-------------------------------+    |
|  | React Chat UI      |<--->| FastAPI Backend               |    |
|  | (Vite + TS)        |     |   /api/chat    (streaming)    |    |
|  | Port 5173          |     |   /api/search  (semantic)     |    |
|  +--------------------+     |   LangGraph Agent             |    |
|                             |   Port 8000                   |    |
|                             +-------------------------------+    |
+------------------------------------------------------------------+
```

### Data Flow: Research and Ingestion

```
User invokes /research "quantum computing"
        |
        v
Claude Code Skill
  1. Web search for authoritative sources
  2. Read and extract key information
  3. Store raw source snapshots to wiki/raw-sources/
  4. Generate/update wiki pages in wiki/pages/
  5. Update cross-references between pages
        |
        v
wiki/pages/*.md  (on disk, committed to git)
        |
        v
Ingestion CLI (make ingest)
  1. Scan wiki/pages/ for new/modified files
  2. Split markdown into semantic chunks (by heading)
  3. Generate embedding vectors per chunk
  4. Upsert chunks + vectors into pgvector
        |
        v
PostgreSQL (wiki_chunks table with vector column)
        |
        v
User asks question in Chat UI
        |
        v
FastAPI /api/chat  ->  LangGraph Agent
  1. Agent receives user message
  2. Agent calls search_knowledge_base tool
  3. Tool queries pgvector (cosine similarity)
  4. Agent synthesizes answer from retrieved chunks
  5. Streams response with source citations back to UI
```

### Component Diagram: LangGraph Agent

```
                    +------------------+
                    |   START          |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    |   agent_node     |
                    |   (LLM call)     |
                    +--------+---------+
                             |
                    +--------+---------+
                    | has tool calls?  |
                    +--+------------+--+
                   yes |            | no
                       v            v
              +--------+----+  +---+--------+
              | tool_node   |  |   END      |
              | (execute)   |  | (respond)  |
              +--------+----+  +------------+
                       |
                       v
                 (back to agent_node)

Available Tools:
  - search_knowledge_base(query: str, top_k: int) -> list[ChunkResult]
  - list_wiki_pages(category: str | None) -> list[PageSummary]
  - get_wiki_page(path: str) -> str
```

## Directory Structure

```
sobriquets/
  CLAUDE.md                          # Project conventions + skill registration
  Makefile                           # Dev commands (up, down, ingest, lint-wiki)
  docker-compose.yml                 # PostgreSQL + pgvector, FastAPI, React
  .env.example                       # Template for environment variables
  
  wiki/                              # The knowledge base (git-tracked)
    schema.md                        # Wiki structure conventions and rules
    raw-sources/                     # Immutable source snapshots
      <topic>/<source-slug>.md       # e.g., quantum-computing/ibm-qiskit-docs.md
    pages/                           # Generated wiki pages
      <topic>/                       # Topic directories
        _index.md                    # Topic overview page
        <entity-or-concept>.md       # Individual wiki pages
  
  skills/                            # Claude Code skills
    research/                        # Research skill
      prompt.md                      # The skill prompt template
  
  backend/                           # Python FastAPI application
    Dockerfile
    pyproject.toml                   # Dependencies (uv/pip)
    sobriquets/
      __init__.py
      main.py                        # FastAPI app entry point
      config.py                      # Settings from env vars
      api/
        __init__.py
        routes.py                    # /api/chat, /api/search, /api/health
      agent/
        __init__.py
        graph.py                     # LangGraph agent definition
        tools.py                     # Agent tools (search, list, get)
        prompts.py                   # System prompts for the agent
      db/
        __init__.py
        models.py                    # SQLAlchemy models
        session.py                   # DB session management
        repository.py               # Query functions
      embeddings/
        __init__.py
        provider.py                  # Embedding provider interface
        sentence_transformers.py     # Local embeddings
        openai_compat.py             # OpenAI-compatible API embeddings
      ingest/
        __init__.py
        __main__.py                  # CLI entry point (python -m sobriquets.ingest)
        chunker.py                   # Markdown chunking logic
        pipeline.py                  # Orchestrates chunk + embed + upsert
        hasher.py                    # Content hash for incremental ingestion
      lint/
        __init__.py
        __main__.py                  # CLI entry point (python -m sobriquets.lint)
        checks.py                    # Orphan, stale, contradiction checks

  frontend/                          # React TypeScript application
    Dockerfile
    package.json
    tsconfig.json
    vite.config.ts
    tailwind.config.ts
    index.html
    src/
      main.tsx
      App.tsx
      components/
        ChatWindow.tsx               # Main chat container
        MessageList.tsx              # Scrollable message history
        MessageBubble.tsx            # Individual message display
        ChatInput.tsx                # Text input + send button
        SourceCitation.tsx           # Expandable source reference
        Sidebar.tsx                  # Topic list / navigation
      hooks/
        useChat.ts                   # Chat state management + streaming
        useSearch.ts                 # Direct search hook
      api/
        client.ts                    # Fetch wrapper for backend API
        types.ts                     # TypeScript interfaces
      styles/
        index.css                    # Tailwind imports + custom styles
```

## Data Models

### PostgreSQL Schema

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Tracks ingested wiki source files and their content hashes
CREATE TABLE wiki_sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_path       TEXT NOT NULL UNIQUE,          -- relative path from wiki/pages/
    content_hash    TEXT NOT NULL,                  -- SHA-256 of file content
    title           TEXT NOT NULL,                  -- extracted from front-matter or first heading
    topic           TEXT NOT NULL,                  -- top-level directory name
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Stores chunked wiki content with embedding vectors
CREATE TABLE wiki_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID NOT NULL REFERENCES wiki_sources(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,              -- order within the source file
    heading         TEXT,                           -- section heading this chunk falls under
    content         TEXT NOT NULL,                  -- the chunk text
    embedding       vector(384) NOT NULL,           -- 384 for all-MiniLM-L6-v2; configurable
    metadata        JSONB DEFAULT '{}',             -- arbitrary metadata (tags, cross-refs)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(source_id, chunk_index)
);

-- HNSW index for fast approximate nearest neighbor search
CREATE INDEX idx_wiki_chunks_embedding ON wiki_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Index for filtering by topic
CREATE INDEX idx_wiki_sources_topic ON wiki_sources(topic);

-- Index for looking up chunks by source
CREATE INDEX idx_wiki_chunks_source_id ON wiki_chunks(source_id);
```

### SQLAlchemy Models (backend/sobriquets/db/models.py)

```python
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import DeclarativeBase, relationship
import uuid
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class WikiSource(Base):
    __tablename__ = "wiki_sources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_path = Column(String, nullable=False, unique=True)
    content_hash = Column(String, nullable=False)
    title = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    ingested_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    chunks = relationship("WikiChunk", back_populates="source", cascade="all, delete-orphan")

class WikiChunk(Base):
    __tablename__ = "wiki_chunks"
    __table_args__ = (UniqueConstraint("source_id", "chunk_index"),)
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("wiki_sources.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    heading = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=False)  # dimension matches model
    metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    source = relationship("WikiSource", back_populates="chunks")
```

### Embedding Dimension Configuration

The vector dimension (384) is the default for `all-MiniLM-L6-v2`. When using OpenAI `text-embedding-3-small` (1536 dims) or other models, the column dimension must match. This is handled by:
- Setting `EMBEDDING_DIMENSION` in `.env`
- Running a migration or re-creating the table when switching models
- The ingestion pipeline validates dimension match before upserting

## API Endpoints

### FastAPI Routes

| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| GET | `/api/health` | Health check | -- | `{ "status": "ok", "wiki_chunks": <count> }` |
| POST | `/api/chat` | Chat with agent (streaming) | `{ "message": str, "session_id": str \| null }` | SSE stream of `ChatEvent` |
| POST | `/api/search` | Semantic search | `{ "query": str, "top_k": int = 5, "topic": str \| null }` | `{ "results": [SearchResult] }` |
| GET | `/api/topics` | List all topics | -- | `{ "topics": [{ "name": str, "page_count": int }] }` |
| GET | `/api/pages/{topic}` | List pages in topic | -- | `{ "pages": [{ "title": str, "path": str }] }` |

### Request/Response Schemas

```python
# Chat
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

class ChatEvent(BaseModel):
    """SSE event types"""
    type: Literal["token", "source", "done", "error"]
    content: str | None = None           # for "token" events
    sources: list[SourceRef] | None = None  # for "source" events

class SourceRef(BaseModel):
    title: str
    file_path: str
    heading: str | None
    relevance_score: float

# Search
class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    topic: str | None = None

class SearchResult(BaseModel):
    chunk_id: str
    content: str
    heading: str | None
    source_title: str
    source_path: str
    topic: str
    score: float
```

### Streaming Protocol

The `/api/chat` endpoint uses Server-Sent Events (SSE). The client connects, sends the message as a POST body, and receives a stream:

```
event: token
data: {"type": "token", "content": "Quantum"}

event: token
data: {"type": "token", "content": " computing"}

event: source
data: {"type": "source", "sources": [{"title": "...", "file_path": "...", "score": 0.87}]}

event: done
data: {"type": "done"}
```

## Frontend Component Hierarchy

```
App
  +-- Sidebar
  |     +-- TopicList (fetches /api/topics)
  |     +-- TopicItem (clickable, filters context)
  +-- ChatWindow
        +-- MessageList
        |     +-- MessageBubble (role: user | assistant)
        |           +-- SourceCitation (expandable, shows source details)
        +-- ChatInput
              +-- textarea (auto-resize)
              +-- SendButton
```

### Key Frontend Behaviors

- **Streaming**: `useChat` hook uses `fetch` with `ReadableStream` to consume SSE from `/api/chat`. Tokens are appended to the current assistant message in real-time.
- **Source citations**: When a `source` event arrives, citations are attached to the current assistant message and rendered as expandable chips below the message text.
- **Auto-scroll**: `MessageList` scrolls to bottom on new tokens; interrupted if user scrolls up.
- **Session management**: A `session_id` (UUID) is generated client-side on first message and sent with subsequent messages for conversation continuity.
- **Responsive layout**: Sidebar collapses on mobile. Chat area fills available width.

## LangGraph Agent Design

### Graph Definition

```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode

# State: just messages (MessagesState provides list[BaseMessage])

def create_agent_graph(tools: list) -> StateGraph:
    graph = StateGraph(MessagesState)
    
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))
    
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    
    return graph.compile()
```

### Agent Node

The agent node calls the configured LLM (default: Claude via Anthropic API or a local model) with:
- A system prompt that describes the Sobriquets knowledge base and instructs the agent to cite sources
- The conversation message history
- Bound tool definitions

### Tools

| Tool | Input | Output | Description |
|------|-------|--------|-------------|
| `search_knowledge_base` | `query: str, top_k: int = 5` | `list[SearchResult]` | Semantic search over pgvector. Returns ranked chunks with metadata. |
| `list_wiki_pages` | `topic: str \| None` | `list[PageSummary]` | Lists available wiki pages, optionally filtered by topic. |
| `get_wiki_page` | `file_path: str` | `str` | Retrieves the full content of a specific wiki page. |

### Tool Selection Strategy

The agent decides which tools to call based on the query:
- Factual questions -> `search_knowledge_base`
- "What topics do I have?" -> `list_wiki_pages`
- "Show me the full page on X" -> `get_wiki_page`
- Complex questions -> multiple `search_knowledge_base` calls with different queries, then synthesis

### LLM Configuration

The agent LLM is configured via `AGENT_LLM_PROVIDER` and `AGENT_LLM_MODEL` environment variables:
- Default: `anthropic` / `claude-sonnet-4-20250514`
- Alternative: `openai` / `gpt-4o` or any OpenAI-compatible endpoint

## Research Skill Specification

### Skill Registration

The skill is registered in `CLAUDE.md` at the repo root:

```markdown
## Skills

### /research
Invoke with: /research <topic>
Prompt file: skills/research/prompt.md
```

### Skill Prompt (skills/research/prompt.md)

The prompt instructs Claude Code to:

1. **Accept** a research topic from the user
2. **Search** the web for authoritative, primary sources (documentation, academic papers, official sites)
3. **Capture raw sources**: For each source, create a file in `wiki/raw-sources/<topic-slug>/<source-slug>.md` with:
   ```markdown
   ---
   url: <source URL>
   retrieved: <ISO 8601 timestamp>
   content_hash: <SHA-256 of captured content>
   authority: <domain/org name>
   ---
   
   <verbatim or lightly-formatted content from the source>
   ```
4. **Generate wiki pages**: Create or update files in `wiki/pages/<topic-slug>/` with:
   ```markdown
   ---
   title: <Page Title>
   topic: <topic-slug>
   created: <ISO 8601>
   updated: <ISO 8601>
   sources:
     - raw-sources/<topic-slug>/<source-slug>.md
   related:
     - pages/<other-topic>/<other-page>.md
   tags:
     - <tag1>
     - <tag2>
   ---
   
   # <Page Title>
   
   ## Overview
   <2-3 paragraph summary>
   
   ## Key Concepts
   <detailed breakdown>
   
   ## See Also
   - [[pages/<related-topic>/<related-page>]]
   
   ## Sources
   - [Source Name](raw-sources/<topic-slug>/<source-slug>.md)
   ```
5. **Create or update the topic index**: `wiki/pages/<topic-slug>/_index.md` listing all pages in the topic
6. **Report** what was created/updated, with a summary of pages and source count

### Skill Output

The skill writes files directly to the wiki directory in the repo. It does not produce structured JSON output -- the markdown files on disk ARE the output, ready for `git add` and ingestion.

### Karpathy Pattern Compliance

| Layer | Implementation | Mutability |
|-------|----------------|------------|
| Raw Sources | `wiki/raw-sources/` | Immutable after creation. Never edited. |
| Wiki Pages | `wiki/pages/` | Regenerated/updated by the skill on re-research. |
| Schema | `wiki/schema.md` + `CLAUDE.md` | Manually maintained by the user. |

## Ingestion Pipeline Design

### CLI Interface

```bash
# Ingest all new/modified wiki pages
python -m sobriquets.ingest

# Ingest a specific topic
python -m sobriquets.ingest --topic quantum-computing

# Force re-ingest everything (ignore hashes)
python -m sobriquets.ingest --force

# Dry run (show what would be ingested)
python -m sobriquets.ingest --dry-run
```

### Pipeline Steps

1. **Scan**: Walk `wiki/pages/` for `.md` files
2. **Filter**: Compare each file's SHA-256 hash against `wiki_sources.content_hash` in the database. Skip unchanged files.
3. **Parse**: Extract front-matter metadata (YAML) and body content from each markdown file.
4. **Chunk**: Split the markdown body into chunks using heading-based splitting:
   - Each H2 or H3 section becomes a chunk
   - Chunks inherit the heading hierarchy as context
   - Maximum chunk size: 1000 tokens (approximately 4000 characters). Sections exceeding this are split at paragraph boundaries.
   - Minimum chunk size: 100 characters. Shorter sections are merged with the next section.
5. **Embed**: Generate embedding vectors for each chunk using the configured embedding provider.
   - Batch processing: embed up to 32 chunks at once for efficiency.
   - The text sent to the embedding model is: `"# {title}\n## {heading}\n\n{content}"` to provide context.
6. **Upsert**: Within a database transaction:
   - Delete existing chunks for modified sources (cascade from `wiki_sources`)
   - Update or insert the `wiki_sources` row with new hash
   - Insert new `wiki_chunks` rows with embeddings
7. **Report**: Print summary (files processed, chunks created, time elapsed).

### Chunking Strategy

```
wiki/pages/quantum-computing/qubits.md
  Front-matter -> metadata for wiki_sources row
  
  "# Qubits" (H1)
    "## Overview" (H2)
      -> Chunk 0: heading="Overview", content="..."
    "## Physical Implementations" (H2)
      "### Superconducting Qubits" (H3)
        -> Chunk 1: heading="Physical Implementations > Superconducting Qubits", content="..."
      "### Trapped Ion Qubits" (H3)
        -> Chunk 2: heading="Physical Implementations > Trapped Ion Qubits", content="..."
    "## See Also" (H2)
      -> Chunk 3: heading="See Also", content="..."
```

## Configuration and Environment Variables

### .env.example

```bash
# === Database ===
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=sobriquets
POSTGRES_USER=sobriquets
POSTGRES_PASSWORD=sobriquets_dev

# === Embeddings ===
# Provider: "sentence_transformers" (local) or "openai" (API)
EMBEDDING_PROVIDER=sentence_transformers
# Model name (for sentence_transformers: model name from HuggingFace)
EMBEDDING_MODEL=all-MiniLM-L6-v2
# Dimension must match the model output
EMBEDDING_DIMENSION=384
# Only needed if EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_API_BASE=https://api.openai.com/v1

# === Agent LLM ===
AGENT_LLM_PROVIDER=anthropic
AGENT_LLM_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=

# === Wiki ===
WIKI_PATH=./wiki
WIKI_PAGES_PATH=./wiki/pages
WIKI_RAW_SOURCES_PATH=./wiki/raw-sources

# === Server ===
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173
```

### docker-compose.yml Structure

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: sobriquets
      POSTGRES_USER: sobriquets
      POSTGRES_PASSWORD: sobriquets_dev
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./backend/db/init.sql:/docker-entrypoint-initdb.d/init.sql

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      POSTGRES_HOST: db
      # ... (other env vars)
    volumes:
      - ./backend:/app
      - ./wiki:/wiki
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend/src:/app/src
    depends_on:
      - backend

volumes:
  pgdata:
```

## Development Workflow

### First-Time Setup

```bash
cp .env.example .env
# Edit .env with your API keys

make up          # docker compose up -d
make migrate     # Apply database migrations
```

### Daily Workflow

```bash
# Start the stack
make up

# Research a new topic (in Claude Code)
/research quantum computing

# Ingest the new wiki content
make ingest

# Open the chat UI
open http://localhost:5173

# Check wiki health
make lint-wiki
```

### Makefile Targets

| Target | Command | Description |
|--------|---------|-------------|
| `up` | `docker compose up -d` | Start all services |
| `down` | `docker compose down` | Stop all services |
| `logs` | `docker compose logs -f` | Tail all logs |
| `ingest` | `docker compose exec backend python -m sobriquets.ingest` | Run ingestion pipeline |
| `ingest-force` | `docker compose exec backend python -m sobriquets.ingest --force` | Force full re-ingestion |
| `lint-wiki` | `docker compose exec backend python -m sobriquets.lint` | Run wiki health checks |
| `migrate` | `docker compose exec backend alembic upgrade head` | Run DB migrations |
| `test` | `docker compose exec backend pytest` | Run backend tests |
| `frontend-dev` | `cd frontend && npm run dev` | Run frontend outside Docker |

## Security Considerations

- **Single-user tool**: No authentication required. The API binds to localhost only in production use. Docker exposes ports to the host only.
- **API keys in .env**: The `.env` file is gitignored. The `.env.example` contains no real keys. The Docker Compose file references environment variables, never hardcodes secrets.
- **No public exposure**: The Docker Compose configuration does not include a reverse proxy or TLS. This is intentional -- the tool runs on a personal machine only.
- **Input sanitization**: The FastAPI endpoints validate input via Pydantic models. The LangGraph agent tools parameterize all SQL queries via SQLAlchemy (no raw string interpolation).
- **Wiki content trust**: Wiki pages are generated by the user's own Claude Code skill and committed to git. The ingestion pipeline trusts this content. There is no user-generated content from untrusted sources.

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Embedding model (default) | `all-MiniLM-L6-v2` (384 dims) | Fast, runs locally on CPU, good quality for general knowledge. No API key needed. |
| Vector DB | PostgreSQL + pgvector | Single database for both relational and vector data. No additional infrastructure. |
| Agent framework | LangGraph | Supports tool-calling loop natively, streaming, and is composable for adding future tools/skills. |
| Frontend bundler | Vite | Fast dev server with HMR. Standard for React/TS projects. |
| Python package manager | uv | Fast, modern, resolves dependencies correctly. Falls back to pip if unavailable. |
| Streaming protocol | SSE (Server-Sent Events) | Simpler than WebSockets for unidirectional streaming. Native browser support via EventSource. Well-supported by FastAPI via `StreamingResponse`. |
| Migrations | Alembic | Standard for SQLAlchemy. Handles pgvector column types. |
| HNSW vs IVFFlat | HNSW | Better recall at small-to-medium scale (under 100k vectors). Acceptable build time for this use case. |

### ADR-001: Use pgvector Instead of a Dedicated Vector Database

**Status**: Proposed
**Context**: The system needs vector similarity search for semantic retrieval. Options include dedicated vector DBs (Pinecone, Qdrant, Weaviate, Chroma) or PostgreSQL with pgvector.
**Decision**: Use pgvector as the vector store, running inside the same PostgreSQL instance as relational data.
**Consequences**: Simpler infrastructure (one database). Slightly less performant than dedicated vector DBs at very large scale (millions of vectors), but more than sufficient for a personal knowledge base. Joins between vector results and relational metadata are trivial. No additional service to manage.

### ADR-002: Heading-Based Chunking Over Fixed-Size Chunking

**Status**: Proposed
**Context**: Markdown wiki pages need to be split into chunks for embedding. Options: fixed token windows with overlap, or semantic splitting by headings.
**Decision**: Split primarily by H2/H3 headings, with a maximum chunk size fallback that splits at paragraph boundaries.
**Consequences**: Chunks align with semantic boundaries (sections), producing more meaningful retrieval results. The heading hierarchy is preserved as context in the chunk metadata, improving search relevance. Trade-off: some chunks may be very short (a "See Also" section) or very long (a dense section), handled by min/max size thresholds.

### ADR-003: SSE Over WebSockets for Chat Streaming

**Status**: Proposed
**Context**: The chat endpoint needs to stream tokens from the LangGraph agent to the frontend in real-time.
**Decision**: Use Server-Sent Events (SSE) via FastAPI's `StreamingResponse` instead of WebSockets.
**Consequences**: Simpler implementation on both server and client. No connection state management. Native browser support. One-directional streaming fits the use case (server -> client tokens; client -> server is a single POST). Trade-off: if bidirectional streaming is needed later (e.g., cancel mid-stream), would need to add a separate cancel endpoint or upgrade to WebSockets.

### ADR-004: Local Sentence-Transformers as Default Embedding Provider

**Status**: Proposed
**Context**: Embeddings are needed for the ingestion pipeline and search. Options: OpenAI API, local sentence-transformers, or other hosted APIs.
**Decision**: Default to local `sentence-transformers` with `all-MiniLM-L6-v2`, with OpenAI API as a configurable alternative.
**Consequences**: Works fully offline. No API costs for embeddings. The model is small (80MB) and fast on CPU. Trade-off: slightly lower embedding quality than `text-embedding-3-small`, but acceptable for a personal wiki. Users who want higher quality can switch to OpenAI via env var.

## Constraints

- The system is single-user. No multi-tenancy, no user management, no RBAC.
- The research skill requires Claude Code with internet access (web search). It cannot run in air-gapped environments.
- The local embedding model (`all-MiniLM-L6-v2`) requires approximately 400MB of disk space and 500MB RAM at inference time.
- Switching embedding models requires re-ingesting all content (different vector dimensions).
- The wiki content must be valid markdown with YAML front-matter. Malformed files will be skipped during ingestion with a warning.

## Out of Scope

- Multi-user support or authentication/authorization
- Deployment to cloud infrastructure (AWS, GCP, etc.)
- Mobile application
- Real-time collaborative editing of wiki pages
- Automatic scheduled re-research (cron-based updates)
- PDF or non-markdown source ingestion
- Fine-tuning or training custom models
- Version history UI for wiki pages (git handles this)
- Full-text search (only semantic/vector search is implemented; full-text can be added later via PostgreSQL tsvector)

## Open Questions

- **Q1**: Should the research skill support incremental updates to existing wiki pages, or always regenerate from scratch? -- Suggested answer: Support both. Default to incremental update (merge new information into existing pages). Provide a `--fresh` flag to regenerate from scratch.
- **Q2**: What LLM should power the LangGraph agent by default? -- Suggested answer: Claude Sonnet via Anthropic API, since the user already has access. Make it configurable for users who prefer OpenAI or local models.
- **Q3**: Should the ingestion pipeline run automatically after the research skill completes? -- Suggested answer: No. Keep them decoupled. The user explicitly runs `make ingest` after reviewing the generated wiki pages. This allows for manual editing before ingestion.
- **Q4**: Should conversation history be persisted to the database? -- Suggested answer: Not for MVP. In-memory session state is sufficient for a personal tool. Add SQLite or PostgreSQL persistence later if needed.
