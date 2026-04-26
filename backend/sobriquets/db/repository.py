import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import delete, distinct, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from sobriquets.db.models import WikiChunk, WikiSource


async def semantic_search(
    session: AsyncSession,
    embedding: list[float],
    top_k: int = 5,
    topic_filter: str | None = None,
) -> list[dict]:
    """Perform cosine similarity search on wiki_chunks."""
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    query = (
        select(
            WikiChunk.id,
            WikiChunk.content,
            WikiChunk.heading,
            WikiChunk.metadata_,
            WikiSource.title.label("source_title"),
            WikiSource.file_path.label("source_path"),
            WikiSource.topic,
            (
                1
                - WikiChunk.embedding.cosine_distance(
                    func.cast(embedding_str, Vector(len(embedding)))
                )
            ).label("score"),
        )
        .join(WikiSource, WikiChunk.source_id == WikiSource.id)
        .order_by(
            WikiChunk.embedding.cosine_distance(
                func.cast(embedding_str, Vector(len(embedding)))
            )
        )
        .limit(top_k)
    )

    if topic_filter:
        query = query.where(WikiSource.topic == topic_filter)

    result = await session.execute(query)
    rows = result.all()

    return [
        {
            "chunk_id": str(row.id),
            "content": row.content,
            "heading": row.heading,
            "source_title": row.source_title,
            "source_path": row.source_path,
            "topic": row.topic,
            "score": float(row.score),
        }
        for row in rows
    ]


async def list_topics(session: AsyncSession) -> list[dict]:
    """Get distinct topics with page counts."""
    query = select(
        WikiSource.topic, func.count(WikiSource.id).label("page_count")
    ).group_by(WikiSource.topic)

    result = await session.execute(query)
    return [
        {"name": row.topic, "page_count": row.page_count} for row in result.all()
    ]


async def list_pages_by_topic(session: AsyncSession, topic: str) -> list[dict]:
    """Get all pages in a topic."""
    query = select(WikiSource.title, WikiSource.file_path).where(
        WikiSource.topic == topic
    )
    result = await session.execute(query)
    return [
        {"title": row.title, "path": row.file_path} for row in result.all()
    ]


async def get_source_by_path(
    session: AsyncSession, file_path: str
) -> WikiSource | None:
    """Look up a source by file path."""
    query = select(WikiSource).where(WikiSource.file_path == file_path)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def upsert_source(
    session: AsyncSession,
    file_path: str,
    content_hash: str,
    title: str,
    topic: str,
) -> WikiSource:
    """Insert or update a wiki source."""
    existing = await get_source_by_path(session, file_path)

    if existing:
        existing.content_hash = content_hash
        existing.title = title
        existing.topic = topic
        existing.updated_at = datetime.now(timezone.utc)
        await session.flush()
        return existing

    source = WikiSource(
        id=uuid.uuid4(),
        file_path=file_path,
        content_hash=content_hash,
        title=title,
        topic=topic,
    )
    session.add(source)
    await session.flush()
    return source


async def delete_chunks_for_source(
    session: AsyncSession, source_id: uuid.UUID
) -> int:
    """Delete all chunks for a source. Returns count deleted."""
    result = await session.execute(
        delete(WikiChunk).where(WikiChunk.source_id == source_id)
    )
    return result.rowcount


async def insert_chunks(
    session: AsyncSession, chunks: list[WikiChunk]
) -> None:
    """Bulk insert chunks."""
    session.add_all(chunks)
    await session.flush()


async def get_chunk_count(session: AsyncSession) -> int:
    """Get total chunk count for health check."""
    result = await session.execute(select(func.count(WikiChunk.id)))
    return result.scalar_one()
