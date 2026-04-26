# Implementation Plan: Sobriquets Personal Knowledge Wiki

## Phase 1: Project Scaffolding & Infrastructure
**Files to create:**
- `docker-compose.yml` — PostgreSQL+pgvector, FastAPI, React services
- `.env.example` — All configuration variables
- `.gitignore` — Updated with .env, node_modules, __pycache__, pgdata, etc.
- `Makefile` — Dev workflow targets (up, down, ingest, lint-wiki, migrate, test)
- `backend/Dockerfile` — Python FastAPI container
- `backend/pyproject.toml` — Python dependencies (fastapi, uvicorn, sqlalchemy, pgvector, langgraph, langchain, sentence-transformers, alembic)
- `frontend/Dockerfile` — React dev container
- `frontend/package.json` — React, TypeScript, Vite, Tailwind dependencies
- `frontend/vite.config.ts` — Vite config with proxy to backend
- `frontend/tsconfig.json` — TypeScript config
- `frontend/tailwind.config.ts` — Tailwind config
- `frontend/index.html` — HTML entry point

## Phase 2: Database & Models
**Files to create:**
- `backend/db/init.sql` — CREATE EXTENSION vector; schema creation
- `backend/sobriquets/__init__.py`
- `backend/sobriquets/config.py` — Pydantic settings from env
- `backend/sobriquets/db/__init__.py`
- `backend/sobriquets/db/models.py` — WikiSource, WikiChunk SQLAlchemy models
- `backend/sobriquets/db/session.py` — Async session factory
- `backend/sobriquets/db/repository.py` — Query functions (semantic search, list topics, etc.)
- `backend/alembic.ini` + `backend/alembic/` — Migration setup

## Phase 3: Embedding Providers
**Files to create:**
- `backend/sobriquets/embeddings/__init__.py`
- `backend/sobriquets/embeddings/provider.py` — Abstract base + factory
- `backend/sobriquets/embeddings/sentence_transformers.py` — Local embedding
- `backend/sobriquets/embeddings/openai_compat.py` — OpenAI API embedding

## Phase 4: Ingestion Pipeline
**Files to create:**
- `backend/sobriquets/ingest/__init__.py`
- `backend/sobriquets/ingest/__main__.py` — CLI entry (argparse)
- `backend/sobriquets/ingest/chunker.py` — Heading-based markdown splitting
- `backend/sobriquets/ingest/pipeline.py` — Scan → filter → parse → chunk → embed → upsert
- `backend/sobriquets/ingest/hasher.py` — SHA-256 content hashing

## Phase 5: LangGraph Agent
**Files to create:**
- `backend/sobriquets/agent/__init__.py`
- `backend/sobriquets/agent/graph.py` — StateGraph with agent_node + ToolNode
- `backend/sobriquets/agent/tools.py` — search_knowledge_base, list_wiki_pages, get_wiki_page
- `backend/sobriquets/agent/prompts.py` — System prompt for the Sobriquets agent

## Phase 6: FastAPI Backend
**Files to create:**
- `backend/sobriquets/main.py` — FastAPI app, CORS, lifespan (init DB, load embeddings)
- `backend/sobriquets/api/__init__.py`
- `backend/sobriquets/api/routes.py` — /api/health, /api/chat (SSE), /api/search, /api/topics, /api/pages/{topic}

## Phase 7: React Frontend
**Files to create:**
- `frontend/src/main.tsx` — React root
- `frontend/src/App.tsx` — Layout with sidebar + chat
- `frontend/src/styles/index.css` — Tailwind imports
- `frontend/src/api/types.ts` — TypeScript interfaces
- `frontend/src/api/client.ts` — Fetch wrapper for backend
- `frontend/src/hooks/useChat.ts` — Chat state + SSE streaming
- `frontend/src/hooks/useSearch.ts` — Search hook
- `frontend/src/components/ChatWindow.tsx`
- `frontend/src/components/MessageList.tsx`
- `frontend/src/components/MessageBubble.tsx`
- `frontend/src/components/ChatInput.tsx`
- `frontend/src/components/SourceCitation.tsx`
- `frontend/src/components/Sidebar.tsx`

## Phase 8: Research Skill & Wiki Schema
**Files to create:**
- `skills/research/prompt.md` — Claude Code research skill prompt
- `wiki/schema.md` — Wiki structure conventions
- `wiki/pages/.gitkeep`
- `wiki/raw-sources/.gitkeep`
- `CLAUDE.md` — Project conventions + skill registration

## Phase 9: Wiki Lint
**Files to create:**
- `backend/sobriquets/lint/__init__.py`
- `backend/sobriquets/lint/__main__.py` — CLI entry
- `backend/sobriquets/lint/checks.py` — Orphan pages, missing refs, stale sources

## Implementation Order
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 (sequential, each builds on prior)

## Coding Agent Instructions
- Work in the worktree at `.claude/worktrees/personal-knowledge-wiki-chatbot`
- Follow the spec in `agent-notes/architect.md` exactly
- Use the directory structure from the spec
- All Python code uses type hints, async where appropriate
- Frontend uses functional components with hooks only
- No class components, no Redux — simple React state + hooks
- Keep implementations practical and complete — this should work end-to-end
