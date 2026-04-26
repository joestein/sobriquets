"""Tests for sobriquets.ingest.pipeline."""
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from sobriquets.ingest.pipeline import _scan_files, _extract_topic


class TestScanFiles:
    def test_finds_md_files_recursively(self, tmp_path: Path) -> None:
        (tmp_path / "topic1").mkdir()
        (tmp_path / "topic1" / "page1.md").write_text("content")
        (tmp_path / "topic1" / "page2.md").write_text("content")
        (tmp_path / "other.txt").write_text("not markdown")

        results = _scan_files(tmp_path)
        assert len(results) == 2
        assert all(p.suffix == ".md" for p in results)

    def test_returns_sorted_list(self, tmp_path: Path) -> None:
        (tmp_path / "b.md").write_text("b")
        (tmp_path / "a.md").write_text("a")
        results = _scan_files(tmp_path)
        names = [p.name for p in results]
        assert names == sorted(names)

    def test_topic_filter_limits_to_subdirectory(self, tmp_path: Path) -> None:
        (tmp_path / "topic1").mkdir()
        (tmp_path / "topic2").mkdir()
        (tmp_path / "topic1" / "page.md").write_text("content")
        (tmp_path / "topic2" / "page.md").write_text("content")

        results = _scan_files(tmp_path, topic_filter="topic1")
        assert len(results) == 1
        assert "topic1" in str(results[0])

    def test_topic_filter_nonexistent_returns_empty(self, tmp_path: Path) -> None:
        results = _scan_files(tmp_path, topic_filter="does-not-exist")
        assert results == []

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        assert _scan_files(tmp_path) == []


class TestExtractTopic:
    def test_nested_path_returns_first_component(self) -> None:
        assert _extract_topic("quantum-computing/qubits.md") == "quantum-computing"

    def test_flat_path_returns_general(self) -> None:
        assert _extract_topic("qubits.md") == "general"

    def test_deeply_nested_returns_first_component(self) -> None:
        assert _extract_topic("science/physics/quantum.md") == "science"


class TestRunPipeline:
    """Integration-style tests for run_pipeline with mocked DB and embeddings."""

    @pytest.mark.asyncio
    async def test_nonexistent_wiki_path_returns_zero_counts(self) -> None:
        from sobriquets.ingest.pipeline import run_pipeline
        from sobriquets.config import Settings

        settings = Settings(WIKI_PAGES_PATH="/nonexistent/path/that/does/not/exist")

        mock_provider = AsyncMock()
        mock_provider.embed = AsyncMock(return_value=[[0.0] * 384])

        result = await run_pipeline(settings, mock_provider)
        assert result["files_scanned"] == 0
        assert result["files_processed"] == 0
        assert result["chunks_created"] == 0

    @pytest.mark.asyncio
    async def test_dry_run_does_not_write_to_db(self, tmp_path: Path) -> None:
        from sobriquets.ingest.pipeline import run_pipeline
        from sobriquets.config import Settings

        pages = tmp_path / "pages"
        pages.mkdir()
        (pages / "test.md").write_text(
            "---\ntitle: Test\ntopic: test\n---\n\n## Content\n\nSome content here.",
            encoding="utf-8",
        )

        settings = Settings(WIKI_PAGES_PATH=str(pages))
        mock_provider = AsyncMock()
        mock_provider.embed = AsyncMock(return_value=[[0.1] * 384])

        with patch("sobriquets.ingest.pipeline.get_session_factory") as mock_sf:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_sf.return_value = MagicMock(return_value=mock_session)

            # Mock get_source_by_path to return None (new file)
            with patch("sobriquets.ingest.pipeline.get_source_by_path", return_value=None):
                result = await run_pipeline(settings, mock_provider, dry_run=True)

        assert result["files_processed"] == 1
        assert result["chunks_created"] == 0  # dry_run skips chunk creation

    @pytest.mark.asyncio
    async def test_unchanged_file_is_skipped(self, tmp_path: Path) -> None:
        from sobriquets.ingest.pipeline import run_pipeline
        from sobriquets.config import Settings
        from sobriquets.db.models import WikiSource

        pages = tmp_path / "pages"
        pages.mkdir()
        md_file = pages / "page.md"
        md_file.write_text(
            "---\ntitle: Test\ntopic: test\n---\n\n## Heading\n\nContent.",
            encoding="utf-8",
        )

        # Compute the real hash so the mock matches
        from sobriquets.ingest.hasher import hash_file
        real_hash = hash_file(md_file)

        settings = Settings(WIKI_PAGES_PATH=str(pages))
        mock_provider = AsyncMock()

        fake_source = MagicMock(spec=WikiSource)
        fake_source.content_hash = real_hash

        with patch("sobriquets.ingest.pipeline.get_session_factory") as mock_sf:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_sf.return_value = MagicMock(return_value=mock_session)

            with patch(
                "sobriquets.ingest.pipeline.get_source_by_path",
                return_value=fake_source,
            ):
                result = await run_pipeline(settings, mock_provider, force=False)

        assert result["files_skipped"] == 1
        assert result["files_processed"] == 0
        # embed should never be called when skipping
        mock_provider.embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_force_flag_bypasses_hash_check(self, tmp_path: Path) -> None:
        from sobriquets.ingest.pipeline import run_pipeline
        from sobriquets.config import Settings
        from sobriquets.db.models import WikiSource, WikiChunk
        import uuid

        pages = tmp_path / "pages"
        pages.mkdir()
        (pages / "page.md").write_text(
            "---\ntitle: Forced\ntopic: test\n---\n\n## Section\n\nForced content.",
            encoding="utf-8",
        )

        settings = Settings(WIKI_PAGES_PATH=str(pages))
        mock_provider = AsyncMock()
        mock_provider.embed = AsyncMock(return_value=[[0.1] * 384])

        fake_source = MagicMock(spec=WikiSource)
        fake_source.id = uuid.uuid4()
        fake_source.content_hash = "old-hash"

        with patch("sobriquets.ingest.pipeline.get_session_factory") as mock_sf:
            mock_session = AsyncMock()
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
            mock_cm.__aexit__ = AsyncMock(return_value=False)
            mock_begin = AsyncMock()
            mock_begin.__aenter__ = AsyncMock(return_value=None)
            mock_begin.__aexit__ = AsyncMock(return_value=False)
            mock_session.begin = MagicMock(return_value=mock_begin)
            mock_sf.return_value = MagicMock(return_value=mock_cm)

            with patch("sobriquets.ingest.pipeline.upsert_source", return_value=fake_source), \
                 patch("sobriquets.ingest.pipeline.delete_chunks_for_source", return_value=0), \
                 patch("sobriquets.ingest.pipeline.insert_chunks", return_value=None):
                result = await run_pipeline(settings, mock_provider, force=True)

        assert result["files_processed"] == 1
        mock_provider.embed.assert_called_once()
