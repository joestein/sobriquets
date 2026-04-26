# Security Agent Notes

## Summary

The Sobriquets personal knowledge wiki codebase demonstrates generally good security practices for a single-user local tool. SQL injection is well-mitigated through consistent SQLAlchemy ORM usage. Path traversal prevention exists in `get_wiki_page`. Secrets are properly gitignored. However, there are several findings requiring attention: an unbounded in-memory session store (DoS risk), Docker containers running as root, missing SSRF protections on the OpenAI-compatible embedding endpoint, a missing `message` length constraint on the chat endpoint, and hardcoded default database credentials in the Settings class.

**Overall assessment: PASS with MEDIUM findings to address.**

No CRITICAL findings. No unmitigated HIGH findings.

## OWASP Top 10 Review

### A01: Broken Access Control
- [N/A] Single-user local tool. No authentication by design (NFR-004). Acceptable.
- [INFO] The `get_wiki_page` tool at `backend/sobriquets/agent/tools.py:106-138` has path traversal prevention via `resolve()` + prefix check. This is functional but see MEDIUM finding below for defense-in-depth improvement.

### A02: Cryptographic Failures
- [OK] SHA-256 used for content hashing in ingestion pipeline (`backend/sobriquets/ingest/hasher.py`).
- [OK] API keys loaded from environment, not hardcoded in source.
- [OK] `.env` is in `.gitignore` (line 19-20).

### A03: Injection
- [OK] All database queries use SQLAlchemy ORM with parameterized queries. No raw SQL string interpolation found.
- [OK] The `embedding_str` construction in `repository.py:18` uses `func.cast()` which is safe -- the embedding values are floats from the embedding provider, not user input.
- [OK] Pydantic models validate API input types.

### A04: Insecure Design
- [MEDIUM] No rate limiting on any endpoint. See finding below.
- [MEDIUM] Unbounded in-memory session storage. See finding below.
- [MEDIUM] No maximum length on `ChatRequest.message`. See finding below.

### A05: Security Misconfiguration
- [MEDIUM] Docker containers run as root. See finding below.
- [LOW] `--reload` flag on uvicorn in production Dockerfile. See finding below.
- [OK] CORS is configurable and defaults to `http://localhost:5173` only.
- [OK] FastAPI debug mode is not explicitly enabled.

### A06: Vulnerable Components
- [OK] Dependencies use minimum version pins with open upper bounds. No known CVEs in the specified minimum versions at time of review.
- [LOW] No lockfile (`requirements.lock`, `uv.lock`, or `package-lock.json`) committed. See finding below.

### A07: Auth Failures
- [N/A] No authentication by design.

### A08: Data Integrity Failures
- [OK] Content hashing ensures ingestion integrity.
- [OK] Raw sources are immutable by convention.

### A09: Logging Failures
- [OK] Structured logging throughout the backend.
- [OK] Error details in `health` endpoint expose `str(e)` but this is acceptable for a local tool.
- [INFO] No sensitive data logged (API keys, passwords) -- confirmed in all logger calls.

### A10: SSRF
- [MEDIUM] OpenAI-compatible embedding provider makes HTTP calls to a user-configured URL with no validation. See finding below.

## STRIDE Analysis

### FastAPI Backend (`/api/*`)
| Threat | Risk | Mitigation |
|--------|------|------------|
| Spoofing | N/A | No auth by design (single-user local) |
| Tampering | Low | SQLAlchemy ORM prevents SQL injection; Pydantic validates input |
| Repudiation | Low | Logging present; acceptable for local tool |
| Information Disclosure | Low | Error messages exposed in health check; no sensitive data |
| Denial of Service | Medium | Unbounded session storage; no rate limiting; no message size limit |
| Elevation of Privilege | N/A | Single-user, no privilege model |

### `get_wiki_page` Agent Tool
| Threat | Risk | Mitigation |
|--------|------|------------|
| Spoofing | N/A | Tool is called by the agent, not directly by users |
| Tampering | N/A | Read-only operation |
| Repudiation | Low | Logged |
| Information Disclosure | Medium | Path traversal mitigation exists but could be stronger |
| Denial of Service | Low | Reads single files; acceptable |
| Elevation of Privilege | N/A | |

### OpenAI-Compatible Embedding Provider
| Threat | Risk | Mitigation |
|--------|------|------------|
| Spoofing | Low | Bearer token auth to remote API |
| Tampering | Low | HTTPS by default |
| Repudiation | Low | httpx logs available |
| Information Disclosure | Medium | API key sent in Authorization header to user-configured URL |
| Denial of Service | Low | 60s timeout configured |
| Elevation of Privilege | N/A | |

## Findings

### [MEDIUM] M1: Unbounded In-Memory Session Storage Enables Memory Exhaustion

- **Location**: `backend/sobriquets/api/routes.py:29` (`_sessions: dict[str, list] = {}`)
- **Description**: The `_sessions` dictionary grows without bound. Each `session_id` creates a new entry storing the full conversation history (all `HumanMessage` and `AIMessage` objects). There is no eviction policy, no maximum session count, and no maximum history length per session. An attacker (or even normal usage over time) can exhaust server memory.
- **Impact**: Memory exhaustion leading to backend crash (DoS). On a long-running local instance, accumulated sessions will leak memory indefinitely.
- **Remediation**: (1) Add a maximum session count with LRU eviction (e.g., `functools.lru_cache` or a bounded dict). (2) Add a maximum message count per session (e.g., keep last 50 messages). (3) Consider a TTL-based eviction for inactive sessions (e.g., 1 hour).
- **Reference**: CWE-400 (Uncontrolled Resource Consumption)

### [MEDIUM] M2: No Input Length Validation on Chat Message

- **Location**: `backend/sobriquets/api/routes.py:47` (`message: str` with no `max_length`)
- **Description**: The `ChatRequest.message` field accepts strings of arbitrary length. A very large message (e.g., many megabytes) would be stored in the session history, sent to the LLM API (potentially incurring large costs), and held in memory.
- **Impact**: Memory exhaustion, excessive LLM API costs, potential upstream API errors.
- **Remediation**: Add `message: str = Field(max_length=32000)` (or an appropriate limit) to the `ChatRequest` Pydantic model. Also add `min_length=1` to reject empty messages.
- **Reference**: CWE-770 (Allocation of Resources Without Limits or Throttling)

### [MEDIUM] M3: SSRF Risk in OpenAI-Compatible Embedding Provider

- **Location**: `backend/sobriquets/embeddings/openai_compat.py:23` (`url = f"{self._api_base}/embeddings"`)
- **Description**: The `OPENAI_API_BASE` environment variable is used directly to construct the target URL for HTTP requests. While this is set by the operator (not by end users), if this value is misconfigured or if any future feature allows runtime override, it could be used to make requests to internal services (e.g., `http://169.254.169.254/` for cloud metadata, `http://db:5432/` for internal services).
- **Impact**: In a Docker environment, the backend container can reach the `db` service and potentially other internal Docker network services. In a cloud environment (if ever deployed), this could access cloud metadata endpoints.
- **Remediation**: (1) Validate that `OPENAI_API_BASE` uses HTTPS scheme (or explicitly allow HTTP for localhost only). (2) Add URL validation in the `OpenAICompatProvider.__init__` to reject private/internal IP ranges. (3) This is lower risk since the value comes from operator-controlled environment variables, not user input.
- **Reference**: CWE-918 (Server-Side Request Forgery)

### [MEDIUM] M4: Docker Containers Run as Root

- **Location**: `backend/Dockerfile` and `frontend/Dockerfile`
- **Description**: Neither Dockerfile creates a non-root user. The backend process (uvicorn) and frontend process (npm/node) both run as root inside their containers. If a vulnerability in the application allows code execution, the attacker has root privileges within the container.
- **Impact**: Container escape risk is elevated when running as root. File system modifications within the container are unrestricted.
- **Remediation**: Add a non-root user to both Dockerfiles:
  ```dockerfile
  RUN useradd -m appuser
  USER appuser
  ```
  For the backend Dockerfile, add this after the `COPY . .` line. For the frontend, after `COPY . .` as well.
- **Reference**: CWE-250 (Execution with Unnecessary Privileges), Docker CIS Benchmark 4.1

### [MEDIUM] M5: Path Traversal Defense-in-Depth Improvement Needed

- **Location**: `backend/sobriquets/agent/tools.py:118-124`
- **Description**: The path traversal check uses `resolve()` followed by `startswith()` string comparison. This is generally effective, but the testing agent noted that on case-insensitive filesystems (macOS HFS+), mixed-case paths could theoretically bypass string prefix matching. Additionally, the current implementation does not reject `..` segments before resolution, meaning symlinks within the wiki directory could potentially escape the boundary.
- **Impact**: If bypassed, an attacker controlling the LLM tool input could read arbitrary files on the filesystem.
- **Remediation**: Add defense-in-depth: (1) Reject any `file_path` containing `..` before resolving: `if ".." in file_path.split("/"):`. (2) Reject paths containing null bytes. (3) Verify that the resolved path has the expected suffix (e.g., `.md`). This is already partially tested but the pre-resolve check should be added.
- **Reference**: CWE-22 (Improper Limitation of a Pathname to a Restricted Directory)

### [LOW] L1: Uvicorn `--reload` in Production Dockerfile

- **Location**: `backend/Dockerfile:16`
- **Description**: The `CMD` uses `--reload` which is a development feature that watches for file changes. This is unnecessary in a production-like container and has a minor performance overhead. More importantly, if source files are mounted via volume (as in docker-compose.yml), file system modifications would be automatically picked up.
- **Impact**: Minor performance overhead; potential for unintended code reloading if volumes are writable.
- **Remediation**: Remove `--reload` from the Dockerfile CMD. Instead, use `--reload` only in the docker-compose.yml command override for development.
- **Reference**: CWE-489 (Active Debug Code)

### [LOW] L2: No Dependency Lockfiles Committed

- **Location**: Project root (missing `backend/uv.lock` or `backend/requirements.lock`; missing `frontend/package-lock.json`)
- **Description**: Neither the Python backend nor the Node.js frontend has a committed lockfile. Version pins in `pyproject.toml` use minimum bounds (`>=`) allowing any newer version. This means builds are not reproducible and a compromised or buggy newer version of a dependency could be pulled automatically.
- **Impact**: Supply chain risk -- a compromised transitive dependency could be installed without detection.
- **Remediation**: (1) Generate and commit `uv.lock` for the backend (or `pip-compile` output). (2) Generate and commit `package-lock.json` for the frontend (`npm install` generates this). (3) Consider using `npm ci` instead of `npm install` in the frontend Dockerfile.
- **Reference**: CWE-1104 (Use of Unmaintained Third Party Components), SLSA Supply Chain Framework

### [LOW] L3: Default Database Password in Settings Defaults

- **Location**: `backend/sobriquets/config.py:10` (`POSTGRES_PASSWORD: str = "sobriquets_dev"`)
- **Description**: The Pydantic Settings class has a hardcoded default password. While this is documented as a development-only default and the `.env.example` also uses this value, having a default password in code means the application will start with a known password if no `.env` file is provided.
- **Impact**: Low for a local-only tool. If the PostgreSQL port (5432) is exposed beyond localhost, the known default credentials could be used to access the database.
- **Remediation**: Consider removing the default for `POSTGRES_PASSWORD` (making it required) or at minimum documenting the need to change it. The docker-compose.yml already references `${POSTGRES_PASSWORD:-sobriquets_dev}` which is acceptable for local dev.
- **Reference**: CWE-798 (Use of Hard-coded Credentials)

### [LOW] L4: Health Endpoint Leaks Internal Error Details

- **Location**: `backend/sobriquets/api/routes.py:103` (`"error": str(e)`)
- **Description**: The health endpoint returns the string representation of database exceptions. This could reveal internal details like database hostnames, connection strings, or SQL errors.
- **Impact**: Low for a local-only tool. Information disclosure risk if the API were ever exposed.
- **Remediation**: Return a generic error message instead of `str(e)`. Log the full error server-side for debugging.
- **Reference**: CWE-209 (Generation of Error Message Containing Sensitive Information)

## Compliance Notes

- **SOC2**: Not applicable -- this is a personal single-user local tool, not a SaaS product.
- **PCI-DSS**: Not applicable -- no payment data handling.
- **NIST 800-53**: Not formally applicable, but the codebase follows reasonable access control (AC), input validation (SI), and audit logging (AU) practices for its scope.
- **GDPR**: Not applicable -- single-user tool with no PII from third parties. Wiki content is user-generated.

## Dependency Audit

- `fastapi>=0.115.0`: No known CVEs at minimum version.
- `sqlalchemy>=2.0.0`: No known CVEs at minimum version.
- `asyncpg>=0.29.0`: No known CVEs at minimum version.
- `pgvector>=0.3.0`: No known CVEs.
- `langgraph>=0.2.0`, `langchain-core>=0.3.0`, `langchain-anthropic>=0.2.0`: Rapidly evolving packages. Pin to specific versions recommended.
- `httpx>=0.27.0`: No known CVEs at minimum version.
- `sentence-transformers>=3.0.0`: No known CVEs.
- `react@^18.3.1`, `vite@^5.4.0`: No known CVEs at minimum version.
- **WARNING**: No lockfiles committed (see L2). Actual installed versions cannot be verified.

## Decisions

- Path traversal prevention in `get_wiki_page` is functional but should be strengthened with pre-resolve `..` rejection as defense-in-depth.
- SSRF risk in OpenAI-compatible provider is accepted as LOW-MEDIUM given that the URL comes from operator-controlled environment variables, not user input.
- All SQL queries use SQLAlchemy ORM -- no injection vectors found.
- CORS configuration is appropriately restricted by default.
- The lack of authentication is explicitly by design for this single-user tool.

## Recommendations for Next Agent

- Documentation agent should document the security model: that this is a localhost-only tool with no authentication, and that exposing it to the network requires adding auth.
- Documentation agent should note the need to change default database credentials for any non-development deployment.
- Build agent should add a lockfile generation step to the CI/build process.
- Build agent should configure the Dockerfiles to run as non-root users.
- Build agent should consider adding `bandit` (Python security linter) and `npm audit` to the CI pipeline.
