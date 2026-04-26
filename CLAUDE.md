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
Invoke with: `/research <topic>`
Prompt file: `.claude/commands/research.md`

Researches a topic using web search, captures raw sources, and generates structured wiki pages. See `.claude/commands/research.md` for full instructions.

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
