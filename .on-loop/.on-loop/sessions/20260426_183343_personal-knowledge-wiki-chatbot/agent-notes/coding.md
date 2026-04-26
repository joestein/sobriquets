# Coding Agent Notes

## Summary
Implemented the complete Sobriquets personal knowledge wiki system: a full-stack application with React TypeScript frontend, Python FastAPI backend, LangGraph agent, pgvector database, ingestion pipeline, wiki linter, and research skill. All 59 files created in the worktree, all Python files pass syntax validation.

## Decisions
- Used module-level singletons for embedding provider and settings in routes/tools to avoid passing through every function call. Initialized during FastAPI lifespan.
- Used `astream_events(version="v2")` for LangGraph streaming to get token-level events for SSE.
- Embedding provider is loaded lazily in sentence_transformers to avoid slow import at module load time.
- In-memory dict for conversation sessions (keyed by session_id) as specified for MVP.
- Path traversal prevention in `get_wiki_page` tool using `resolve()` and prefix check.
- Used `cosine_distance` from pgvector SQLAlchemy integration for semantic search, converting to similarity score (1 - distance).

## Files Modified
- `.gitignore` -- Replaced with project-specific ignores (pgdata, node_modules, .env, etc.)
- `.env.example` -- All configuration variables for DB, embeddings, agent, wiki, server
- `docker-compose.yml` -- 3 services: db (pgvector:pg16), backend, frontend with healthcheck
- `Makefile` -- 8 targets: up, down, logs, ingest, ingest-force, lint-wiki, migrate, test, frontend-dev
- `CLAUDE.md` -- Project description, skill registration, dev workflow
- `backend/pyproject.toml` -- All Python dependencies
- `backend/Dockerfile` -- Python 3.11 slim, pip install, uvicorn
- `backend/db/init.sql` -- CREATE EXTENSION vector
- `backend/sobriquets/config.py` -- Pydantic BaseSettings with all env vars
- `backend/sobriquets/db/models.py` -- WikiSource and WikiChunk SQLAlchemy models
- `backend/sobriquets/db/session.py` -- Async engine/session factory
- `backend/sobriquets/db/repository.py` -- 7 repository functions (semantic_search, list_topics, etc.)
- `backend/sobriquets/embeddings/provider.py` -- Abstract base + factory
- `backend/sobriquets/embeddings/sentence_transformers.py` -- Local embedding with lazy load
- `backend/sobriquets/embeddings/openai_compat.py` -- httpx-based OpenAI API client
- `backend/sobriquets/ingest/__main__.py` -- CLI with --topic, --force, --dry-run
- `backend/sobriquets/ingest/pipeline.py` -- Full scan/filter/parse/chunk/embed/upsert pipeline
- `backend/sobriquets/ingest/chunker.py` -- Heading-based markdown splitter with merge/split
- `backend/sobriquets/ingest/hasher.py` -- SHA-256 file hashing
- `backend/sobriquets/agent/graph.py` -- LangGraph StateGraph with agent/tools nodes
- `backend/sobriquets/agent/tools.py` -- 3 LangChain tools: search, list, get
- `backend/sobriquets/agent/prompts.py` -- System prompt for the Sobriquets agent
- `backend/sobriquets/main.py` -- FastAPI app with lifespan, CORS, router
- `backend/sobriquets/api/routes.py` -- 5 endpoints: health, chat (SSE), search, topics, pages
- `backend/sobriquets/lint/checks.py` -- 4 checks: orphans, frontmatter, cross-refs, stale sources
- `backend/sobriquets/lint/__main__.py` -- Lint CLI entry point
- `frontend/package.json` -- React, TypeScript, Vite, Tailwind deps
- `frontend/Dockerfile` -- Node 20 slim, npm install, dev server
- `frontend/vite.config.ts` -- Proxy /api to backend
- `frontend/tsconfig.json` -- Strict React TS config
- `frontend/tailwind.config.ts` -- Content paths
- `frontend/postcss.config.js` -- Tailwind + autoprefixer
- `frontend/index.html` -- Root HTML
- `frontend/src/main.tsx` -- React root
- `frontend/src/App.tsx` -- Layout with responsive sidebar + chat
- `frontend/src/styles/index.css` -- Tailwind imports + scrollbar utilities
- `frontend/src/api/types.ts` -- All TypeScript interfaces
- `frontend/src/api/client.ts` -- Fetch wrapper with SSE streaming
- `frontend/src/hooks/useChat.ts` -- Chat state management + streaming
- `frontend/src/hooks/useSearch.ts` -- Search hook
- `frontend/src/components/ChatWindow.tsx` -- Chat container
- `frontend/src/components/MessageList.tsx` -- Scrollable messages with auto-scroll
- `frontend/src/components/MessageBubble.tsx` -- User/assistant message rendering
- `frontend/src/components/ChatInput.tsx` -- Textarea with auto-resize, Ctrl+Enter
- `frontend/src/components/SourceCitation.tsx` -- Expandable source chip
- `frontend/src/components/Sidebar.tsx` -- Topic list with refresh
- `wiki/schema.md` -- Wiki structure conventions
- `wiki/pages/.gitkeep` -- Placeholder
- `wiki/raw-sources/.gitkeep` -- Placeholder
- `skills/research/prompt.md` -- Full research skill prompt
- All `__init__.py` files (8 total) -- Empty package markers

## Issues Found
- None -- all Python files compile successfully

## Recommendations for Next Agent
- Test the Docker Compose stack end-to-end (docker compose up, then ingest, then chat)
- Verify SSE streaming works correctly in the browser with the React frontend
- Test the ingestion pipeline with sample markdown files containing frontmatter
- Verify the semantic search returns correct cosine similarity scores
- Test path traversal prevention in the get_wiki_page tool
- Check that the LangGraph agent correctly calls tools and streams responses
- Verify the chunker handles edge cases: empty files, files with no headings, very large sections
