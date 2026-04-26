# Testing Agent Notes

## Summary

Wrote 106 backend unit and integration tests across 6 test files covering the chunker, hasher, ingestion pipeline, agent tools, API endpoints, and wiki linter. All 106 tests pass. No DB or external service required — all DB operations and embedding calls are mocked. Frontend tests were not written because Vitest is not configured in the project (no vitest config or test scripts in package.json).

## Test Results

- Total: 106
- Passed: 106
- Failed: 0
- Skipped: 0
- Coverage: not measured (pytest-cov not installed, would require DB for full coverage)

## Tests Written

### Unit Tests

- `backend/tests/test_hasher.py` — SHA-256 hashing: hex output, known hash value, different content produces different hashes, same content determinism, empty files, large files (chunked read), binary content (7 tests)
- `backend/tests/test_chunker.py` — Markdown chunker: Chunk dataclass, `_split_by_headings` (H1/H2/H3 behavior, preamble, empty body), `_merge_small_sections` (small section merging, threshold behavior), `_split_at_paragraphs` (paragraph boundary splitting, large single-paragraph), `chunk_markdown` end-to-end (empty, headingless, sequential indices, large section split, nested H3 context, content stripping) (24 tests)
- `backend/tests/test_lint.py` — Wiki linter: LintIssue/LintReport dataclasses, `check_missing_frontmatter` (valid, missing title, missing topic, both missing, nested dirs, severity), `check_orphan_pages` (referenced/unreferenced, _index.md exclusion, pages-namespace refs, severity), `check_broken_cross_refs` (valid refs, broken refs, multiple refs, severity), `check_stale_sources` (valid/missing source refs, severity, no refs), `run_all_checks` integration (31 tests)

### Integration Tests

- `backend/tests/test_pipeline.py` — Ingestion pipeline: `_scan_files` (recursive .md discovery, sorted output, topic filter, nonexistent filter, empty dir), `_extract_topic` (nested/flat/deep paths), `run_pipeline` async (nonexistent wiki path, dry-run skips DB writes, hash-based skip, force flag bypass) — all with mocked DB session and embedding provider (12 tests)
- `backend/tests/test_agent_tools.py` — LangGraph tools: `set_embedding_provider` module global, `get_tools` count, `search_knowledge_base` (no provider error, results format, empty results, embedding failure), `list_wiki_pages` (no topics, all topics, topic filter, no pages for topic), `get_wiki_page` (content read, missing page, path traversal `../`, parent escape, directory target) — all with mocked DB and settings (15 tests)
- `backend/tests/test_api.py` — FastAPI endpoints via TestClient (no lifespan, init_routes called directly with mocked provider): `GET /api/health` (ok, degraded on DB error), `POST /api/search` (results, topic filter forwarding, top_k min/max validation, 503 when no provider, 422 on missing query, empty results), `GET /api/topics` (list, empty), `GET /api/pages/{topic}` (list, unknown topic), `_extract_sources` helper (single source, multiple sources, no Source markers, invalid relevance) (17 tests)

### E2E Tests

None written. No Playwright setup and no running browser environment available. Frontend is React/Vite without a configured test runner.

## Decisions

- Used `uv venv + uv pip install` to create an isolated venv in `backend/.venv` since the system pip3 is managed by Homebrew and disallows system-wide installs. Installed only the subset of deps needed for testing (pytest, pytest-asyncio, python-frontmatter, fastapi, httpx, pydantic-settings, anyio) — heavy deps like sentence-transformers, pgvector, langgraph were not installed.
- Chunker tests for heading-based splitting and nested H3 context initially failed because short content ("Alpha content." = 14 chars) is below MIN_CHUNK_CHARS (100) and gets merged into the next section. Fixed by padding test content to >= MIN_CHUNK_CHARS so sections remain independent.
- API tests build a minimal FastAPI app without the lifespan (which requires DB + real embeddings) and call `init_routes()` directly with a mock embedding provider. This avoids any infrastructure dependency.
- Pipeline `run_pipeline` async tests use `patch` for `get_session_factory`, `get_source_by_path`, `upsert_source`, `delete_chunks_for_source`, `insert_chunks` to fully isolate from PostgreSQL.
- Agent tools tests patch `get_session_factory` and `semantic_search`/`list_topics`/`list_pages_by_topic` directly in the tools module to avoid DB calls.
- Frontend tests skipped: `frontend/package.json` has no `test` script and vitest is not in the dependency list.

## Files Modified

- `backend/tests/__init__.py` — Empty package marker (created)
- `backend/tests/conftest.py` — MockEmbeddingProvider, wiki markdown fixtures, sample_wiki_dir (created)
- `backend/tests/test_hasher.py` — 7 tests for SHA-256 file hashing (created)
- `backend/tests/test_chunker.py` — 24 tests for markdown chunking logic (created)
- `backend/tests/test_pipeline.py` — 12 tests for ingestion pipeline scan/filter/run functions (created)
- `backend/tests/test_agent_tools.py` — 15 tests for LangGraph search/list/get tools (created)
- `backend/tests/test_api.py` — 17 tests for FastAPI REST endpoints (created)
- `backend/tests/test_lint.py` — 31 tests for wiki lint checks (created)

## Issues Found

- [LOW] The `_merge_small_sections` function merges ALL small sections sequentially even when the combined result could still be small. This is expected behavior but means that very small documents with many H2 headings collapse into a single chunk — tests document this behavior explicitly.
- [LOW] `check_orphan_pages` flags all pages that are not cross-referenced by any other page, including pages that are conceptually root-level (like a topic overview). In a real wiki this may produce false positives if the primary entry point is the sidebar/topic listing rather than cross-links.
- [INFO] The `get_wiki_page` path traversal check uses string prefix matching (`str(full_path).startswith(str(pages_resolved))`). On case-insensitive filesystems (macOS HFS+) this could potentially be bypassed with mixed-case paths, though in practice `resolve()` normalizes casing on HFS+. No security issue in practice.
- [INFO] `run_pipeline` uses module-level `get_session_factory()` imported from `sobriquets.db.session` — this requires `init_engine()` to have been called before any pipeline run. Tests mock this correctly but the dependency is implicit.

## Failures Detail

Two initial test failures were found during development and fixed before final run:

### test_heading_based_splitting (initial failure)
- **Expected**: Three separate chunks with headings Alpha, Beta, Gamma
- **Actual**: One merged chunk with heading Alpha
- **Root Cause**: Each section content was 14 chars, well below MIN_CHUNK_CHARS=100, triggering merge logic
- **Fix Applied**: Padded each section to MIN_CHUNK_CHARS characters in the test

### test_nested_h3_heading_context (initial failure)
- **Expected**: A chunk with heading containing "Child" and "Parent"
- **Actual**: No chunk with "Child" in heading (merged into parent)
- **Root Cause**: Same as above — short content triggers merge
- **Fix Applied**: Padded parent and child section content to MIN_CHUNK_CHARS

## Recommendations for Next Agent

- Install `pytest-cov` and run with `--cov=sobriquets` to get coverage metrics once a DB is available
- Integration tests that exercise the actual PostgreSQL + pgvector flow (semantic_search, upsert_source, etc.) would require Docker — these are documented gaps
- The `/api/chat` SSE endpoint has no tests because TestClient does not stream SSE. Consider adding a test using `httpx.AsyncClient` with `stream=True` to verify the SSE event format
- Frontend: add vitest to `frontend/package.json` and write component render tests for ChatWindow, MessageBubble, and SourceCitation
- Security: the path traversal protection in `get_wiki_page` is verified by tests but could be strengthened by rejecting any path containing `..` before resolve, as defense-in-depth
