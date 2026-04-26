import json
import logging
import uuid
from typing import AsyncGenerator, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from sobriquets.agent.graph import create_agent_graph
from sobriquets.agent.tools import set_embedding_provider
from sobriquets.config import Settings, get_settings
from sobriquets.db.repository import (
    get_chunk_count,
    list_pages_by_topic,
    list_topics,
    semantic_search,
)
from sobriquets.db.session import get_session, get_session_factory
from sobriquets.embeddings.provider import EmbeddingProvider, get_embedding_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# In-memory session storage for conversation history
_sessions: dict[str, list] = {}

# Module-level refs set during app startup
_embedding_provider: EmbeddingProvider | None = None
_settings: Settings | None = None


def init_routes(settings: Settings, embedding_provider: EmbeddingProvider) -> None:
    """Initialize route-level dependencies."""
    global _embedding_provider, _settings
    _embedding_provider = embedding_provider
    _settings = settings


# --- Request/Response Models ---


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class SourceRef(BaseModel):
    title: str
    file_path: str
    heading: str | None = None
    relevance_score: float = 0.0


class ChatEvent(BaseModel):
    type: Literal["token", "source", "done", "error"]
    content: str | None = None
    sources: list[SourceRef] | None = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    topic: str | None = None


class SearchResult(BaseModel):
    chunk_id: str
    content: str
    heading: str | None
    source_title: str
    source_path: str
    topic: str
    score: float


class TopicResponse(BaseModel):
    name: str
    page_count: int


class PageInfo(BaseModel):
    title: str
    path: str


# --- Endpoints ---


@router.get("/health")
async def health():
    """Health check with chunk count."""
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            count = await get_chunk_count(session)
        return {"status": "ok", "wiki_chunks": count}
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return {"status": "degraded", "wiki_chunks": 0, "error": str(e)}


@router.post("/chat")
async def chat(request: ChatRequest):
    """Chat with the knowledge base agent. Returns SSE stream."""
    if _settings is None or _embedding_provider is None:
        raise HTTPException(
            status_code=503, detail="Service not fully initialized"
        )

    session_id = request.session_id or str(uuid.uuid4())

    # Get or create conversation history
    if session_id not in _sessions:
        _sessions[session_id] = []

    history = _sessions[session_id]
    history.append(HumanMessage(content=request.message))

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            graph = create_agent_graph(_settings)
            full_response = ""
            sources_emitted = False

            async for event in graph.astream_events(
                {"messages": list(history)},
                version="v2",
            ):
                kind = event.get("event", "")

                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        token = chunk.content
                        if isinstance(token, str):
                            full_response += token
                            chat_event = ChatEvent(
                                type="token", content=token
                            )
                            yield f"event: token\ndata: {chat_event.model_dump_json()}\n\n"

                elif kind == "on_tool_end" and not sources_emitted:
                    # Extract source references from tool results
                    output = event.get("data", {}).get("output", "")
                    if isinstance(output, str) and "Source:" in output:
                        sources = _extract_sources(output)
                        if sources:
                            chat_event = ChatEvent(
                                type="source", sources=sources
                            )
                            yield f"event: source\ndata: {chat_event.model_dump_json()}\n\n"
                            sources_emitted = True

            # Store the assistant response
            if full_response:
                history.append(AIMessage(content=full_response))

            done_event = ChatEvent(type="done")
            yield f"event: done\ndata: {done_event.model_dump_json()}\n\n"

        except Exception as e:
            logger.error("Chat stream error: %s", e)
            error_event = ChatEvent(
                type="error", content="An error occurred processing your request."
            )
            yield f"event: error\ndata: {error_event.model_dump_json()}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-Id": session_id,
        },
    )


@router.post("/search")
async def search(request: SearchRequest):
    """Semantic search over wiki chunks."""
    if _embedding_provider is None:
        raise HTTPException(
            status_code=503, detail="Embedding provider not initialized"
        )

    try:
        embeddings = await _embedding_provider.embed([request.query])
        query_embedding = embeddings[0]
    except Exception as e:
        logger.error("Embedding generation failed: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to generate query embedding"
        )

    session_factory = get_session_factory()
    async with session_factory() as session:
        results = await semantic_search(
            session,
            query_embedding,
            top_k=request.top_k,
            topic_filter=request.topic,
        )

    return {
        "results": [
            SearchResult(
                chunk_id=r["chunk_id"],
                content=r["content"],
                heading=r["heading"],
                source_title=r["source_title"],
                source_path=r["source_path"],
                topic=r["topic"],
                score=r["score"],
            )
            for r in results
        ]
    }


@router.get("/topics")
async def topics():
    """List all topics with page counts."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        topic_list = await list_topics(session)

    return {
        "topics": [
            TopicResponse(name=t["name"], page_count=t["page_count"])
            for t in topic_list
        ]
    }


@router.get("/pages/{topic}")
async def pages(topic: str):
    """List pages in a topic."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        page_list = await list_pages_by_topic(session, topic)

    return {
        "pages": [
            PageInfo(title=p["title"], path=p["path"]) for p in page_list
        ]
    }


def _extract_sources(tool_output: str) -> list[SourceRef]:
    """Extract source references from search tool output."""
    sources: list[SourceRef] = []
    current: dict = {}

    for line in tool_output.split("\n"):
        line = line.strip()
        if line.startswith("Source: "):
            if current:
                sources.append(_make_source_ref(current))
                current = {}
            # Parse "Title (path)"
            text = line[7:]
            if "(" in text and text.endswith(")"):
                paren_idx = text.rfind("(")
                current["title"] = text[:paren_idx].strip()
                current["file_path"] = text[paren_idx + 1 : -1]
            else:
                current["title"] = text
                current["file_path"] = ""
        elif line.startswith("Section: "):
            current["heading"] = line[9:]
        elif line.startswith("Relevance: "):
            try:
                current["score"] = float(line[11:])
            except ValueError:
                current["score"] = 0.0

    if current:
        sources.append(_make_source_ref(current))

    return sources


def _make_source_ref(data: dict) -> SourceRef:
    return SourceRef(
        title=data.get("title", "Unknown"),
        file_path=data.get("file_path", ""),
        heading=data.get("heading"),
        relevance_score=data.get("score", 0.0),
    )
