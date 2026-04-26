# Build Agent Notes

## Summary

Created GitHub Actions CI pipeline with two jobs (backend tests, frontend typecheck). Updated the Makefile with a `help` target, inline documentation, and a `test-local` target for running tests without Docker. Added a `typecheck` npm script to `frontend/package.json`. Verified `docker-compose.yml` and `pyproject.toml` pytest config — both are correct as-is.

## Decisions

- Used `npm install` instead of `npm ci` in CI because no `package-lock.json` is committed. The alternative would be to generate and commit a lockfile, which is the better long-term choice but out of scope for this agent.
- CI installs only the lightweight subset of Python deps needed for tests (no sentence-transformers, pgvector, langgraph) — this mirrors what the testing agent did when running tests locally and keeps CI fast.
- Added CI trigger for `on-loop/**` branches in addition to main and PRs so the feature branch used by on-loop sessions also gets checked.
- Left the existing `test` Makefile target (Docker-based) unchanged. Added `test-local` alongside it so developers can run tests without spinning up Docker.
- `docker-compose.yml` healthcheck is correct: `pg_isready -U ... -d ...` with 5s interval/timeout and 5 retries. Backend `depends_on: db: condition: service_healthy` ensures correct startup order.
- `pyproject.toml` already has `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` and `testpaths = ["tests"]` — no separate `pytest.ini` needed.

## Files Modified

- `.github/workflows/ci.yml` — Created. Two-job CI: backend pytest + frontend tsc --noEmit
- `Makefile` — Added `help` target with inline docs, added `test-local` and `typecheck` targets
- `frontend/package.json` — Added `"typecheck": "tsc --noEmit"` script

## CI Pipeline

- Triggers: push to `main` or `on-loop/**`, pull requests targeting `main`
- Job 1 — Backend Tests:
  1. Checkout
  2. Set up Python 3.11 with pip cache
  3. Install test deps (pip, no heavy ML libs)
  4. pytest tests/ -v
- Job 2 — Frontend Type Check:
  1. Checkout
  2. Set up Node 20
  3. npm install
  4. npm run typecheck (tsc --noEmit)
- Estimated duration: 2-3 minutes (Python install cached after first run; Node install uncached until lockfile is committed)

## Issues Found

- [LOW] No `frontend/package-lock.json` committed. This means npm dep versions are not pinned and CI cannot use `npm ci` (faster, reproducible). Recommend running `npm install` in the frontend directory and committing the generated lockfile.
- [INFO] `docker-compose.yml` backend service mounts `./backend:/app` as a volume, which means code changes on the host are reflected immediately without rebuilding the image. Good for dev, but note that the Dockerfile `COPY` steps are shadowed in dev mode.

## Recommendations for Next Agent

- Commit `frontend/package-lock.json` (run `cd frontend && npm install` and add the lockfile to git). Once committed, update CI to use `npm ci` and add the npm cache step back.
- Consider adding `pytest-cov` to the test deps and running with `--cov=sobriquets --cov-report=term-missing` to get coverage numbers in CI output.
- If the project grows, split the pip install step into a requirements file (`pip freeze > requirements-test.txt`) so CI cache invalidation is reliable.
