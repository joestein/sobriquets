"""Tests for sobriquets.agent.tools."""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest


class TestSetEmbeddingProvider:
    def test_set_embedding_provider_updates_module_global(self) -> None:
        import sobriquets.agent.tools as tools_module
        mock_provider = MagicMock()
        original = tools_module._embedding_provider
        try:
            tools_module.set_embedding_provider(mock_provider)
            assert tools_module._embedding_provider is mock_provider
        finally:
            tools_module._embedding_provider = original

    def test_get_tools_returns_list_of_three(self) -> None:
        from sobriquets.agent.tools import get_tools
        tools = get_tools()
        assert len(tools) == 3


class TestSearchKnowledgeBase:
    @pytest.mark.asyncio
    async def test_returns_error_when_no_provider(self) -> None:
        import sobriquets.agent.tools as tools_module
        original = tools_module._embedding_provider
        try:
            tools_module._embedding_provider = None
            result = await tools_module.search_knowledge_base.ainvoke({"query": "test"})
            assert "Error" in result
            assert "not initialized" in result.lower() or "Embedding provider" in result
        finally:
            tools_module._embedding_provider = original

    @pytest.mark.asyncio
    async def test_returns_results_when_search_succeeds(self) -> None:
        import sobriquets.agent.tools as tools_module

        mock_provider = AsyncMock()
        mock_provider.embed = AsyncMock(return_value=[[0.1] * 384])

        mock_results = [
            {
                "source_title": "Quantum Overview",
                "source_path": "quantum/overview.md",
                "heading": "Qubits",
                "score": 0.92,
                "content": "A qubit is the basic unit of quantum information.",
            }
        ]

        original = tools_module._embedding_provider
        try:
            tools_module._embedding_provider = mock_provider

            with patch("sobriquets.agent.tools.get_session_factory") as mock_sf, \
                 patch("sobriquets.agent.tools.semantic_search", return_value=mock_results):
                mock_session = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=False)
                mock_sf.return_value = MagicMock(return_value=mock_session)

                result = await tools_module.search_knowledge_base.ainvoke({"query": "qubits"})

            assert "Quantum Overview" in result
            assert "quantum/overview.md" in result
            assert "0.920" in result
        finally:
            tools_module._embedding_provider = original

    @pytest.mark.asyncio
    async def test_returns_no_results_message_when_empty(self) -> None:
        import sobriquets.agent.tools as tools_module

        mock_provider = AsyncMock()
        mock_provider.embed = AsyncMock(return_value=[[0.1] * 384])

        original = tools_module._embedding_provider
        try:
            tools_module._embedding_provider = mock_provider

            with patch("sobriquets.agent.tools.get_session_factory") as mock_sf, \
                 patch("sobriquets.agent.tools.semantic_search", return_value=[]):
                mock_session = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=False)
                mock_sf.return_value = MagicMock(return_value=mock_session)

                result = await tools_module.search_knowledge_base.ainvoke({"query": "unknown topic"})

            assert "No relevant results" in result
        finally:
            tools_module._embedding_provider = original

    @pytest.mark.asyncio
    async def test_embedding_failure_returns_error_message(self) -> None:
        import sobriquets.agent.tools as tools_module

        mock_provider = AsyncMock()
        mock_provider.embed = AsyncMock(side_effect=RuntimeError("GPU out of memory"))

        original = tools_module._embedding_provider
        try:
            tools_module._embedding_provider = mock_provider
            result = await tools_module.search_knowledge_base.ainvoke({"query": "test"})
            assert "Error" in result
        finally:
            tools_module._embedding_provider = original


class TestListWikiPages:
    @pytest.mark.asyncio
    async def test_no_topics_returns_empty_message(self) -> None:
        import sobriquets.agent.tools as tools_module

        with patch("sobriquets.agent.tools.get_session_factory") as mock_sf, \
             patch("sobriquets.agent.tools.list_topics", return_value=[]):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_sf.return_value = MagicMock(return_value=mock_session)

            result = await tools_module.list_wiki_pages.ainvoke({})

        assert "No topics" in result or "ingestion" in result.lower()

    @pytest.mark.asyncio
    async def test_lists_all_topics_when_no_filter(self) -> None:
        import sobriquets.agent.tools as tools_module

        mock_topics = [
            {"name": "quantum-computing", "page_count": 5},
            {"name": "machine-learning", "page_count": 3},
        ]

        with patch("sobriquets.agent.tools.get_session_factory") as mock_sf, \
             patch("sobriquets.agent.tools.list_topics", return_value=mock_topics):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_sf.return_value = MagicMock(return_value=mock_session)

            result = await tools_module.list_wiki_pages.ainvoke({})

        assert "quantum-computing" in result
        assert "machine-learning" in result
        assert "5" in result

    @pytest.mark.asyncio
    async def test_lists_pages_for_specific_topic(self) -> None:
        import sobriquets.agent.tools as tools_module

        mock_pages = [
            {"title": "Qubits", "path": "quantum-computing/qubits.md"},
            {"title": "Overview", "path": "quantum-computing/overview.md"},
        ]

        with patch("sobriquets.agent.tools.get_session_factory") as mock_sf, \
             patch("sobriquets.agent.tools.list_pages_by_topic", return_value=mock_pages):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_sf.return_value = MagicMock(return_value=mock_session)

            result = await tools_module.list_wiki_pages.ainvoke({"topic": "quantum-computing"})

        assert "Qubits" in result
        assert "Overview" in result

    @pytest.mark.asyncio
    async def test_no_pages_for_topic_returns_message(self) -> None:
        import sobriquets.agent.tools as tools_module

        with patch("sobriquets.agent.tools.get_session_factory") as mock_sf, \
             patch("sobriquets.agent.tools.list_pages_by_topic", return_value=[]):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_sf.return_value = MagicMock(return_value=mock_session)

            result = await tools_module.list_wiki_pages.ainvoke({"topic": "nonexistent"})

        assert "No pages found" in result or "nonexistent" in result


class TestGetWikiPage:
    @pytest.mark.asyncio
    async def test_returns_page_content(self, tmp_path: Path) -> None:
        import sobriquets.agent.tools as tools_module

        pages = tmp_path / "pages"
        pages.mkdir()
        (pages / "note.md").write_text("# Hello\n\nContent here.", encoding="utf-8")

        with patch("sobriquets.agent.tools.get_settings") as mock_gs:
            mock_settings = MagicMock()
            mock_settings.WIKI_PAGES_PATH = str(pages)
            mock_gs.return_value = mock_settings

            result = await tools_module.get_wiki_page.ainvoke({"file_path": "note.md"})

        assert "Content here" in result

    @pytest.mark.asyncio
    async def test_missing_page_returns_not_found(self, tmp_path: Path) -> None:
        import sobriquets.agent.tools as tools_module

        pages = tmp_path / "pages"
        pages.mkdir()

        with patch("sobriquets.agent.tools.get_settings") as mock_gs:
            mock_settings = MagicMock()
            mock_settings.WIKI_PAGES_PATH = str(pages)
            mock_gs.return_value = mock_settings

            result = await tools_module.get_wiki_page.ainvoke({"file_path": "does-not-exist.md"})

        assert "not found" in result.lower() or "Page not found" in result

    @pytest.mark.asyncio
    async def test_path_traversal_is_blocked(self, tmp_path: Path) -> None:
        """Attempting ../../../etc/passwd should return an error."""
        import sobriquets.agent.tools as tools_module

        pages = tmp_path / "pages"
        pages.mkdir()

        with patch("sobriquets.agent.tools.get_settings") as mock_gs:
            mock_settings = MagicMock()
            mock_settings.WIKI_PAGES_PATH = str(pages)
            mock_gs.return_value = mock_settings

            result = await tools_module.get_wiki_page.ainvoke(
                {"file_path": "../../../etc/passwd"}
            )

        assert "Error" in result or "Invalid" in result

    @pytest.mark.asyncio
    async def test_path_traversal_with_encoded_dots_is_blocked(self, tmp_path: Path) -> None:
        """Absolute paths that escape pages dir should be rejected."""
        import sobriquets.agent.tools as tools_module

        pages = tmp_path / "pages"
        pages.mkdir()
        # Create a file outside pages dir
        secret = tmp_path / "secret.txt"
        secret.write_text("secret data", encoding="utf-8")

        with patch("sobriquets.agent.tools.get_settings") as mock_gs:
            mock_settings = MagicMock()
            mock_settings.WIKI_PAGES_PATH = str(pages)
            mock_gs.return_value = mock_settings

            # Attempt to traverse to parent
            result = await tools_module.get_wiki_page.ainvoke(
                {"file_path": "../secret.txt"}
            )

        assert "Error" in result or "Invalid" in result
        assert "secret data" not in result

    @pytest.mark.asyncio
    async def test_directory_path_returns_not_a_file(self, tmp_path: Path) -> None:
        import sobriquets.agent.tools as tools_module

        pages = tmp_path / "pages"
        pages.mkdir()
        subdir = pages / "subdir"
        subdir.mkdir()

        with patch("sobriquets.agent.tools.get_settings") as mock_gs:
            mock_settings = MagicMock()
            mock_settings.WIKI_PAGES_PATH = str(pages)
            mock_gs.return_value = mock_settings

            result = await tools_module.get_wiki_page.ainvoke({"file_path": "subdir"})

        assert "Not a file" in result or "not found" in result.lower()
