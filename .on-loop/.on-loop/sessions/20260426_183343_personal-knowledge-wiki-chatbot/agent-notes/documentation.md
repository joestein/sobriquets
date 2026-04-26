# Documentation Agent Notes

## Summary

Created or updated four documentation files covering the full Sobriquets system:

1. **`README.md`** (worktree root) — Full rewrite of the stub (was 2 lines). Covers project description, quick start, prerequisites, architecture with Mermaid diagram and three-layer pattern table, tech stack, project structure, API reference table, configuration table, development commands, and security notes.

2. **`CLAUDE.md`** (worktree root) — Already complete and correct. Skill registration points to `.claude/commands/research.md` which is where the file lives. No changes needed.

3. **`backend/README.md`** — New file. Covers setup with and without Docker, full API endpoint reference with request/response examples (health, chat/SSE, search, topics, pages), ingestion CLI usage, wiki linter usage, running tests, and module structure.

4. **`frontend/README.md`** — New file. Covers setup with and without Docker, component hierarchy, key behaviors (streaming, source citations, session management, auto-scroll), hooks reference, API client description, and tech stack.

## Decisions

- Kept README.md focused on the end-to-end workflow (research -> ingest -> chat) rather than exhaustive technical detail, since that lives in the component READMEs.
- Used a Mermaid flowchart (not a sequence diagram) for the main README — it shows the system topology more clearly than a flow of steps.
- Did not document the `/api/chat` SSE endpoint in the main README API table beyond a brief note — the streaming protocol detail is in `backend/README.md` where developers looking at the backend code will find it.
- Documented `skills/research/prompt.md` location as "legacy" in the project structure since the coding agent moved the file to `.claude/commands/research.md` — the active path.
- Did not fabricate configuration defaults that aren't in `.env.example`. All values in the configuration table come directly from the file.

## Files Modified

- `README.md` (worktree root) — Full rewrite; was a 2-line stub
- `backend/README.md` — Created new
- `frontend/README.md` — Created new
- `CLAUDE.md` (worktree root) — Verified correct; no changes made

## Issues Found

- [LOW] The coding agent created `skills/research/prompt.md` initially, then moved the skill to `.claude/commands/research.md` and updated CLAUDE.md. The `skills/` directory entry in plan.md and architect.md still refers to the old location. This is a documentation-only discrepancy (the code is correct); no runtime impact.
- [INFO] Frontend has no test runner configured (`package.json` has no `test` script, vitest not installed). The frontend README documents this gap from the testing agent notes.
- [INFO] `backend/README.md` notes that conversation history is in-memory only (per the MVP spec), so restarting the backend clears all sessions. This is expected behavior but worth noting for users.

## Recommendations for Next Agent

- If vitest is added to the frontend, update `frontend/README.md` with the test command and what is covered.
- If persistent conversation history is implemented (database-backed sessions), update `backend/README.md`'s chat endpoint section to document the session persistence behavior.
- The wiki `schema.md` file could be cross-referenced from the main README under a "Wiki Conventions" section if the wiki grows large.
- Consider adding example `/research` output (a sample wiki page skeleton) to the main README or CLAUDE.md to give first-time users a concrete picture of what the skill produces.
