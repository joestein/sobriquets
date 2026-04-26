# Reviewer Agent Notes

## Summary

Comprehensive review of the Sobriquets personal knowledge wiki system. The codebase is well-structured, implements all spec requirements, and follows good practices for a personal-use application. 106/106 tests pass. One blocking issue found: the Vite proxy configuration in the frontend Docker container targets `localhost:8000` which resolves to the frontend container itself, not the backend -- this breaks the Docker Compose workflow. All other findings are non-blocking.

## Verdict: REQUEST_CHANGES

## Review Checklist Results

### Correctness: ISSUES

- [HIGH] **Vite proxy broken in Docker Compose**: `frontend/vite.config.ts:11` proxies `/api` to `http://localhost:8000`. When running inside the Docker frontend container, `localhost` is the frontend container, not the backend service. The Vite dev server proxy will fail to reach the backend. This must be changed to `http://backend:8000` for Docker or made configurable via environment variable. This is the one issue that prevents `docker compose up` from producing a working system (NFR-001 violation).
- All 10 functional requirements (FR-001 through FR-010) are implemented.
- LangGraph agent graph, tools, and streaming are correctly wired.
- Ingestion pipeline handles incremental hashing, batched embeddings, and transactional upsert correctly.
- Chunker heading stack logic is correct for H2/H3 nesting.
- Path traversal prevention in `get_wiki_page` is functional.

### Security: PASS

- All security agent findings (M1-M5) were documented. None are CRITICAL or HIGH for a single-user local tool.
- No new security issues found beyond what the security agent reported.
- SQLAlchemy ORM used throughout; no raw SQL injection vectors.
- `.env` in `.gitignore`; no secrets in code.

### Performance: PASS

- Embedding batching (EMBED_BATCH_SIZE=32) is correct.
- HNSW index configured on wiki_chunks.embedding with reasonable parameters.
- Lazy model loading in SentenceTransformerProvider avoids startup cost until first use.
- `asyncio.to_thread` for sentence-transformers avoids blocking the event loop.
- Connection pool configured (pool_size=5, max_overflow=10) -- appropriate for single-user.

### Code Quality: PASS

- Clean, idiomatic Python with type hints throughout.
- Frontend uses functional components and hooks exclusively, per conventions.
- Good separation of concerns: repository pattern for DB, provider pattern for embeddings, clean API routes.
- [LOW] `sse-starlette>=2.0.0` in `pyproject.toml` is never imported. The code uses FastAPI's `StreamingResponse` directly. This is dead dependency weight.
- [LOW] `pytest` and `pytest-asyncio` are listed in main `dependencies` rather than a `[project.optional-dependencies]` test group.
- No dead code observed in the source modules.

### Testing: PASS

- 106/106 tests pass covering hasher, chunker, pipeline, agent tools, API routes, and lint.
- Tests properly mock DB and embedding provider, avoiding infrastructure dependencies.
- Path traversal tests verify `../` escape attempts.
- Known gaps (SSE streaming, frontend, DB integration) are documented and acceptable for initial delivery.

### Documentation: PASS

- README includes architecture diagram, quick start, API reference, and configuration table.
- CLAUDE.md correctly registers the `/research` slash command.
- Backend and frontend each have their own README with setup and usage instructions.
- Research skill prompt is thorough and follows the Karpathy three-layer pattern.

### Build & CI: ISSUES

- [HIGH] Vite proxy misconfiguration prevents Docker Compose from working end-to-end (see Correctness section).
- [LOW] CI installs a subset of dependencies manually rather than using `pip install -e .` -- this means CI does not validate that `pyproject.toml` is installable. Currently fine since the heavy deps (sentence-transformers, pgvector) are not needed for unit tests.
- [LOW] No lockfiles committed (documented by security agent as L2).

## Issues Found

- [HIGH] Vite proxy target broken in Docker -- `frontend/vite.config.ts:11` -- Change proxy target from `http://localhost:8000` to `http://backend:8000` or use an env var like `VITE_API_TARGET` with fallback.
- [LOW] Unused dependency `sse-starlette` -- `backend/pyproject.toml:22` -- Remove from dependencies since StreamingResponse is used instead.
- [LOW] Test dependencies in main deps -- `backend/pyproject.toml:20-21` -- Move `pytest` and `pytest-asyncio` to `[project.optional-dependencies]`.
- [LOW] `--reload` in production Dockerfile -- `backend/Dockerfile:16` -- Remove from Dockerfile CMD; use docker-compose command override for dev.

## Decisions

- Verdict is REQUEST_CHANGES due to the Vite proxy configuration issue which is a functional blocker for the primary development workflow (`docker compose up`). This is a one-line fix but it prevents the system from working as specified.
- All security findings from the security agent are accepted as documented -- none require blocking the release of a personal single-user tool.
- The absence of frontend tests and DB integration tests is acceptable for initial delivery given the scope.

## Files Reviewed

- `backend/sobriquets/main.py` -- Clean lifespan setup, correct initialization order
- `backend/sobriquets/config.py` -- Proper Pydantic settings with env file support
- `backend/sobriquets/api/routes.py` -- All 5 endpoints implemented, SSE streaming correct
- `backend/sobriquets/db/models.py` -- SQLAlchemy models match spec schema
- `backend/sobriquets/db/repository.py` -- Clean repository pattern, parameterized queries
- `backend/sobriquets/db/session.py` -- Async session factory with proper guards
- `backend/sobriquets/agent/graph.py` -- LangGraph StateGraph correctly wired
- `backend/sobriquets/agent/tools.py` -- 3 tools with path traversal protection
- `backend/sobriquets/agent/prompts.py` -- Well-crafted system prompt
- `backend/sobriquets/embeddings/provider.py` -- Clean abstract base + factory
- `backend/sobriquets/embeddings/sentence_transformers.py` -- Lazy loading, async via to_thread
- `backend/sobriquets/embeddings/openai_compat.py` -- httpx with timeout
- `backend/sobriquets/ingest/pipeline.py` -- Complete pipeline with incremental hashing
- `backend/sobriquets/ingest/chunker.py` -- Heading-based splitting with merge/split logic
- `backend/sobriquets/ingest/hasher.py` -- Correct chunked SHA-256
- `backend/sobriquets/ingest/__main__.py` -- CLI with argparse
- `backend/sobriquets/lint/checks.py` -- 4 lint checks with clear issue reporting
- `backend/sobriquets/lint/__main__.py` -- CLI with exit codes
- `backend/pyproject.toml` -- Dependencies listed
- `backend/Dockerfile` -- Functional but has --reload in CMD
- `frontend/src/App.tsx` -- Responsive layout with sidebar toggle
- `frontend/src/api/client.ts` -- SSE streaming via ReadableStream
- `frontend/src/api/types.ts` -- TypeScript interfaces match backend models
- `frontend/src/hooks/useChat.ts` -- State management with streaming
- `frontend/src/hooks/useSearch.ts` -- Not reviewed (simple fetch wrapper)
- `frontend/src/components/ChatWindow.tsx` -- Clean composition
- `frontend/src/components/MessageList.tsx` -- Auto-scroll with user-scroll detection
- `frontend/src/components/MessageBubble.tsx` -- User/assistant styling
- `frontend/src/components/ChatInput.tsx` -- Auto-resize textarea
- `frontend/src/components/SourceCitation.tsx` -- Expandable citation chips
- `frontend/src/components/Sidebar.tsx` -- Topic listing with refresh
- `frontend/vite.config.ts` -- BLOCKING: proxy misconfigured for Docker
- `frontend/package.json` -- Dependencies correct
- `frontend/Dockerfile` -- Simple Node container
- `docker-compose.yml` -- Services, healthcheck, volumes correct
- `Makefile` -- Dev targets with help docs
- `.github/workflows/ci.yml` -- Backend tests + frontend typecheck
- `.claude/commands/research.md` -- Thorough research skill prompt
- `wiki/schema.md` -- Wiki conventions documented
- `CLAUDE.md` -- Project conventions and skill registration
- `backend/db/init.sql` -- pgvector extension creation

## Commendations

- The chunker implementation is thoughtful -- heading stack tracking for H3 context, merge logic for small sections, paragraph-boundary splitting for large sections.
- Embedding provider abstraction is clean -- lazy-loaded sentence-transformers with `asyncio.to_thread` to avoid blocking the event loop is a good pattern.
- The research skill prompt is exceptionally well-written -- clear structure, immutability rules for raw sources, and practical guidelines.
- The SSE streaming implementation in the frontend using `ReadableStream` with a manual line parser is robust and avoids the `EventSource` API limitation of being GET-only.
- Good use of transactional upsert in the ingestion pipeline -- delete old chunks + insert new within `session.begin()`.
- The auto-scroll behavior in `MessageList.tsx` with user-scroll detection is a nice UX touch.

## Recommendations for Next Agent

**Required fix (blocking):**
1. Change `frontend/vite.config.ts` proxy target from `http://localhost:8000` to `http://backend:8000` to fix Docker Compose networking. Alternatively, use an environment variable so it works both locally (`localhost:8000`) and in Docker (`backend:8000`).

**Non-blocking improvements (if time permits):**
2. Remove `sse-starlette` from `backend/pyproject.toml` dependencies.
3. Move `pytest` and `pytest-asyncio` to `[project.optional-dependencies]`.
4. Remove `--reload` from `backend/Dockerfile` CMD.
