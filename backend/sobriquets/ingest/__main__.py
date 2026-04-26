import argparse
import asyncio
import logging
import sys

from sobriquets.config import get_settings
from sobriquets.db.models import Base
from sobriquets.db.session import get_engine, init_engine
from sobriquets.embeddings.provider import get_embedding_provider
from sobriquets.ingest.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest wiki markdown files into pgvector"
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Only ingest pages for a specific topic",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-ingest all files (ignore content hashes)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be ingested without making changes",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    asyncio.run(_run(args))


async def _run(args: argparse.Namespace) -> None:
    settings = get_settings()
    init_engine(settings)

    # Create tables if they don't exist
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    embedding_provider = get_embedding_provider(settings)

    summary = await run_pipeline(
        settings=settings,
        embedding_provider=embedding_provider,
        topic_filter=args.topic,
        force=args.force,
        dry_run=args.dry_run,
    )

    print("\n--- Ingestion Summary ---")
    print(f"  Files scanned:   {summary['files_scanned']}")
    print(f"  Files processed: {summary['files_processed']}")
    print(f"  Files skipped:   {summary.get('files_skipped', 0)}")
    print(f"  Chunks created:  {summary['chunks_created']}")
    print(f"  Time elapsed:    {summary['elapsed_seconds']}s")


if __name__ == "__main__":
    main()
