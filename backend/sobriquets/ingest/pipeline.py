import logging
import time
import uuid
from pathlib import Path

import frontmatter

from sobriquets.config import Settings
from sobriquets.db.models import WikiChunk
from sobriquets.db.repository import (
    delete_chunks_for_source,
    get_source_by_path,
    insert_chunks,
    upsert_source,
)
from sobriquets.db.session import get_session_factory
from sobriquets.embeddings.provider import EmbeddingProvider
from sobriquets.ingest.chunker import chunk_markdown
from sobriquets.ingest.hasher import hash_file

logger = logging.getLogger(__name__)

EMBED_BATCH_SIZE = 32


async def run_pipeline(
    settings: Settings,
    embedding_provider: EmbeddingProvider,
    topic_filter: str | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    """Run the ingestion pipeline.

    Returns a summary dict with counts of files processed, chunks created, etc.
    """
    start_time = time.time()
    pages_path = Path(settings.WIKI_PAGES_PATH)

    if not pages_path.exists():
        logger.warning("Wiki pages path does not exist: %s", pages_path)
        return {"files_scanned": 0, "files_processed": 0, "chunks_created": 0}

    # Step 1: Scan for markdown files
    md_files = _scan_files(pages_path, topic_filter)
    logger.info("Found %d markdown files", len(md_files))

    files_processed = 0
    chunks_created = 0
    files_skipped = 0

    session_factory = get_session_factory()

    for file_path in md_files:
        rel_path = str(file_path.relative_to(pages_path))
        content_hash = hash_file(file_path)

        # Step 2: Check if file has changed
        if not force:
            async with session_factory() as session:
                existing = await get_source_by_path(session, rel_path)
                if existing and existing.content_hash == content_hash:
                    logger.debug("Skipping unchanged file: %s", rel_path)
                    files_skipped += 1
                    continue

        if dry_run:
            logger.info("[DRY RUN] Would process: %s", rel_path)
            files_processed += 1
            continue

        # Step 3: Parse frontmatter and content
        try:
            post = frontmatter.load(str(file_path))
        except Exception:
            logger.warning("Failed to parse frontmatter for %s, skipping", rel_path)
            continue

        title = post.get("title", file_path.stem.replace("-", " ").title())
        topic = _extract_topic(rel_path)
        body = post.content

        # Step 4: Chunk the content
        chunks = chunk_markdown(body)
        if not chunks:
            logger.warning("No chunks generated for %s, skipping", rel_path)
            continue

        # Step 5: Generate embeddings (batched)
        texts_to_embed = [
            f"# {title}\n## {c.heading or 'Content'}\n\n{c.content}"
            for c in chunks
        ]

        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts_to_embed), EMBED_BATCH_SIZE):
            batch = texts_to_embed[i : i + EMBED_BATCH_SIZE]
            batch_embeddings = await embedding_provider.embed(batch)
            all_embeddings.extend(batch_embeddings)

        # Step 6: Upsert within a transaction
        async with session_factory() as session:
            async with session.begin():
                source = await upsert_source(
                    session, rel_path, content_hash, title, topic
                )

                await delete_chunks_for_source(session, source.id)

                chunk_models = [
                    WikiChunk(
                        id=uuid.uuid4(),
                        source_id=source.id,
                        chunk_index=chunk.index,
                        heading=chunk.heading,
                        content=chunk.content,
                        embedding=all_embeddings[idx],
                        metadata_={},
                    )
                    for idx, chunk in enumerate(chunks)
                ]
                await insert_chunks(session, chunk_models)

                chunks_created += len(chunk_models)
                files_processed += 1

        logger.info(
            "Processed %s: %d chunks", rel_path, len(chunk_models)
        )

    elapsed = time.time() - start_time
    summary = {
        "files_scanned": len(md_files),
        "files_processed": files_processed,
        "files_skipped": files_skipped,
        "chunks_created": chunks_created,
        "elapsed_seconds": round(elapsed, 2),
    }

    logger.info(
        "Ingestion complete: %d files processed, %d chunks created in %.2fs",
        files_processed,
        chunks_created,
        elapsed,
    )

    return summary


def _scan_files(
    pages_path: Path, topic_filter: str | None = None
) -> list[Path]:
    """Walk the pages directory for .md files, optionally filtered by topic."""
    if topic_filter:
        topic_path = pages_path / topic_filter
        if not topic_path.exists():
            logger.warning("Topic directory not found: %s", topic_path)
            return []
        return sorted(topic_path.rglob("*.md"))

    return sorted(pages_path.rglob("*.md"))


def _extract_topic(rel_path: str) -> str:
    """Extract the topic from a relative path like 'quantum-computing/qubits.md'."""
    parts = Path(rel_path).parts
    if len(parts) > 1:
        return parts[0]
    return "general"
