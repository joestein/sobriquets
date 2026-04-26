import json
import logging
from pathlib import Path

from langchain_core.tools import tool

from sobriquets.config import get_settings
from sobriquets.db.repository import (
    list_pages_by_topic,
    list_topics,
    semantic_search,
)
from sobriquets.db.session import get_session_factory
from sobriquets.embeddings.provider import EmbeddingProvider

logger = logging.getLogger(__name__)

# Module-level reference set during app startup
_embedding_provider: EmbeddingProvider | None = None


def set_embedding_provider(provider: EmbeddingProvider) -> None:
    """Set the embedding provider for tools to use."""
    global _embedding_provider
    _embedding_provider = provider


def get_tools() -> list:
    """Return the list of agent tools."""
    return [search_knowledge_base, list_wiki_pages, get_wiki_page]


@tool
async def search_knowledge_base(query: str, top_k: int = 5) -> str:
    """Search the personal knowledge base for information relevant to the query.

    Use this tool for factual questions, concept lookups, or finding relevant information.
    It performs semantic search over embedded wiki content.

    Args:
        query: The search query in natural language.
        top_k: Number of results to return (default 5).
    """
    if _embedding_provider is None:
        return "Error: Embedding provider not initialized."

    try:
        embeddings = await _embedding_provider.embed([query])
        query_embedding = embeddings[0]
    except Exception as e:
        logger.error("Failed to generate query embedding: %s", e)
        return f"Error generating embedding for query: {e}"

    session_factory = get_session_factory()
    async with session_factory() as session:
        results = await semantic_search(
            session, query_embedding, top_k=top_k
        )

    if not results:
        return "No relevant results found in the knowledge base."

    formatted = []
    for r in results:
        formatted.append(
            f"Source: {r['source_title']} ({r['source_path']})\n"
            f"Section: {r['heading'] or 'General'}\n"
            f"Relevance: {r['score']:.3f}\n"
            f"Content:\n{r['content']}\n"
        )

    return "\n---\n".join(formatted)


@tool
async def list_wiki_pages(topic: str | None = None) -> str:
    """List available wiki pages, optionally filtered by topic.

    Use this when the user asks what topics or pages are available.

    Args:
        topic: Optional topic name to filter by. If None, lists all topics with counts.
    """
    session_factory = get_session_factory()

    async with session_factory() as session:
        if topic:
            pages = await list_pages_by_topic(session, topic)
            if not pages:
                return f"No pages found for topic '{topic}'."
            lines = [f"Pages in topic '{topic}':"]
            for p in pages:
                lines.append(f"  - {p['title']} ({p['path']})")
            return "\n".join(lines)
        else:
            topics = await list_topics(session)
            if not topics:
                return "No topics found in the knowledge base. Run ingestion first."
            lines = ["Available topics:"]
            for t in topics:
                lines.append(f"  - {t['name']} ({t['page_count']} pages)")
            return "\n".join(lines)


@tool
async def get_wiki_page(file_path: str) -> str:
    """Retrieve the full content of a specific wiki page.

    Use this when you need the complete text of a page, not just search snippets.

    Args:
        file_path: The relative path of the wiki page (e.g., 'quantum-computing/qubits.md').
    """
    settings = get_settings()
    pages_path = Path(settings.WIKI_PAGES_PATH)
    full_path = pages_path / file_path

    # Prevent path traversal
    try:
        full_path = full_path.resolve()
        pages_resolved = pages_path.resolve()
        if not str(full_path).startswith(str(pages_resolved)):
            return "Error: Invalid file path."
    except Exception:
        return "Error: Invalid file path."

    if not full_path.exists():
        return f"Page not found: {file_path}"

    if not full_path.is_file():
        return f"Not a file: {file_path}"

    try:
        content = full_path.read_text(encoding="utf-8")
        return content
    except Exception as e:
        logger.error("Failed to read wiki page %s: %s", file_path, e)
        return f"Error reading page: {e}"
