# Implementation Plan: Autoresearch Skill Upgrade

## Scope
3 files modified — this is a prompt rewrite + schema updates, no backend code.

## Files to Modify

### 1. `.claude/commands/research.md` — FULL REWRITE
Replace the single-pass research prompt with the autoresearch iterative loop prompt:
- Parse args: `<topic> [--effort <1-5>] [--loops <N>] [--focus <subtopic>]`
- Default effort=2, loops from effort matrix
- Loop state machine: SEARCH → EVALUATE → STRESS_TEST (loop 2+) → SYNTHESIZE → LOG
- Source scoring rubric (authority/relevance/recency, 0-5 each, threshold 8/15)
- Progressive search depth (L1=overview, L2=academic, L3=contrarian, L4=meta, L5=gap-fill)
- Stress-test: contradictions, unsupported claims, missing perspectives, outdated info
- Additive page updates only (never delete content)
- Research log append to `wiki/pages/<topic>/research-log.md`
- Convergence detection at effort 3+ (zero-delta → early termination)
- Final report with per-loop and aggregate stats

### 2. `wiki/schema.md` — UPDATE
- Add new optional front-matter fields: `confidence` (low/medium/high), `research_loops` (int), `last_stressed` (ISO 8601)
- Add research-log page type documentation
- Note that research-log.md is excluded from vector ingestion

### 3. `CLAUDE.md` — UPDATE
- Replace `/research` skill section with new signature showing --effort, --loops, --focus flags
- Brief description of iterative behavior

## Implementation Order
1 → 2 → 3 (sequential, each builds on prior understanding)

## Coding Agent Notes
- Work in worktree at `.claude/worktrees/autoresearch-skill-upgrade`
- The research.md rewrite is the bulk of the work — it's a ~300-line prompt
- Read the existing files first before modifying
- Follow the spec in architect.md exactly for the effort matrix, scoring rubric, and log format
- Keep backward compatibility: `/research <topic>` with no flags = effort 2
