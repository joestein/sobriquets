# Sobriquets

Personal knowledge wiki system following Karpathy's three-layer LLM Wiki pattern.

## Project Structure

- `wiki/` - Knowledge base (git-tracked markdown files)
  - `raw-sources/` - Immutable source snapshots
  - `pages/` - Generated wiki pages
  - `schema.md` - Wiki conventions
- `backend/` - Python FastAPI with LangGraph agent and pgvector
- `frontend/` - React TypeScript chat interface
- `.claude/commands/` - Claude Code slash commands

## Skills

### /research
Invoke with: `/research <topic> [--effort <1-5>] [--loops <N>] [--focus <subtopic>]`
Prompt file: `.claude/commands/research.md`

Researches a topic using iterative autonomous loops. Each loop searches for sources, evaluates them (authority/relevance/recency scoring), stress-tests findings against existing wiki content, synthesizes validated information into wiki pages, and logs its work.

- **--effort**: Controls depth (1=quick, 2=standard default, 3=thorough, 4=exhaustive, 5=definitive)
- **--loops**: Override the default loop count for the chosen effort level
- **--focus**: Constrain research to a specific subtopic

See `.claude/commands/research.md` for the full skill prompt.

## Development Workflow

```bash
# First-time setup
cp .env.example .env
# Edit .env with your API keys (ANTHROPIC_API_KEY required for chat)

# Start all services
make up

# Research a new topic (run this as a Claude Code slash command)
/research <topic>

# Ingest wiki content into the vector database
make ingest

# Open the chat UI
open http://localhost:5173

# Check wiki health
make lint-wiki

# View logs
make logs

# Stop services
make down
```

## Tech Stack

- **Database**: PostgreSQL 16 + pgvector (cosine similarity search)
- **Backend**: Python 3.11, FastAPI, SQLAlchemy (async), LangGraph, LangChain
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2) by default, OpenAI API optional
- **Agent LLM**: Claude Sonnet via Anthropic API (configurable)

## Conventions

- Wiki page filenames use kebab-case: `my-topic/my-page.md`
- All wiki pages require `title` and `topic` front-matter fields
- Cross-references use `[[pages/<topic>/<page>]]` syntax
- Raw sources are immutable -- never edit after creation
- Run `make ingest` after adding or modifying wiki pages
- Run `make lint-wiki` to check for broken references and orphan pages
