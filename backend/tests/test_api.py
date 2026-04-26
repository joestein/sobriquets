"""Tests for sobriquets.api.routes using FastAPI TestClient."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sobriquets.api.routes import router, init_routes


# ---------------------------------------------------------------------------
# App fixture: build a minimal FastAPI app without the lifespan that requires DB
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_embedding_provider():
    provider = AsyncMock()
    provider.embed = AsyncMock(return_value=[[0.1] * 384])
    return provider


@pytest.fixture
def app(mock_embedding_provider):
    """Minimal FastAPI app for testing routes with mocked dependencies."""
    from sobriquets.config import Settings
    test_settings = Settings()

    test_app = FastAPI()
    test_app.include_router(router)

    # Initialize routes with mock provider/settings (bypass lifespan)
    init_routes(test_settings, mock_embedding_provider)

    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_ok_when_db_works(self, client: TestClient) -> None:
        with patch("sobriquets.api.routes.get_session_factory") as mock_sf, \
             patch("sobriquets.api.routes.get_chunk_count", return_value=42):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_sf.return_value = MagicMock(return_value=mock_session)

            response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["wiki_chunks"] == 42

    def test_health_returns_degraded_when_db_fails(self, client: TestClient) -> None:
        with patch("sobriquets.api.routes.get_session_factory") as mock_sf, \
             patch("sobriquets.api.routes.get_chunk_count", side_effect=Exception("DB down")):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_sf.return_value = MagicMock(return_value=mock_session)

            response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["wiki_chunks"] == 0


# ---------------------------------------------------------------------------
# POST /api/search
# ---------------------------------------------------------------------------

class TestSearchEndpoint:
    def test_search_returns_results(
        self, client: TestClient, mock_embedding_provider
    ) -> None:
        mock_results = [
            {
                "chunk_id": "abc-123",
                "content": "Quantum entanglement explained.",
                "heading": "Entanglement",
                "source_title": "Quantum Overview",
                "source_path": "quantum/overview.md",
                "topic": "quantum-computing",
                "score": 0.88,
            }
        ]

        with patch("sobriquets.api.routes.get_session_factory") as mock_sf, \
             patch("sobriquets.api.routes.semantic_search", return_value=mock_results):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_sf.return_value = MagicMock(return_value=mock_session)

            response = client.post(
                "/api/search",
                json={"query": "quantum entanglement", "top_k": 5},
            )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["source_title"] == "Quantum Overview"
        assert data["results"][0]["score"] == 0.88

    def test_search_with_topic_filter(
        self, client: TestClient, mock_embedding_provider
    ) -> None:
        with patch("sobriquets.api.routes.get_session_factory") as mock_sf, \
             patch("sobriquets.api.routes.semantic_search", return_value=[]) as mock_search:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_sf.return_value = MagicMock(return_value=mock_session)

            response = client.post(
                "/api/search",
                json={"query": "test", "top_k": 3, "topic": "science"},
            )

        assert response.status_code == 200
        # Verify semantic_search was called with topic_filter
        mock_search.assert_called_once()
        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs.get("topic_filter") == "science"

    def test_search_top_k_validation_min(self, client: TestClient) -> None:
        response = client.post(
            "/api/search",
            json={"query": "test", "top_k": 0},
        )
        assert response.status_code == 422

    def test_search_top_k_validation_max(self, client: TestClient) -> None:
        response = client.post(
            "/api/search",
            json={"query": "test", "top_k": 21},
        )
        assert response.status_code == 422

    def test_search_returns_503_when_provider_not_initialized(
        self, app: FastAPI
    ) -> None:
        import sobriquets.api.routes as routes_module
        original = routes_module._embedding_provider
        try:
            routes_module._embedding_provider = None
            local_client = TestClient(app)
            response = local_client.post(
                "/api/search",
                json={"query": "test"},
            )
            assert response.status_code == 503
        finally:
            routes_module._embedding_provider = original

    def test_search_missing_query_field_returns_422(self, client: TestClient) -> None:
        response = client.post("/api/search", json={})
        assert response.status_code == 422

    def test_search_empty_results_returns_empty_list(
        self, client: TestClient
    ) -> None:
        with patch("sobriquets.api.routes.get_session_factory") as mock_sf, \
             patch("sobriquets.api.routes.semantic_search", return_value=[]):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_sf.return_value = MagicMock(return_value=mock_session)

            response = client.post("/api/search", json={"query": "nothing"})

        assert response.status_code == 200
        assert response.json()["results"] == []


# ---------------------------------------------------------------------------
# GET /api/topics
# ---------------------------------------------------------------------------

class TestTopicsEndpoint:
    def test_topics_returns_list(self, client: TestClient) -> None:
        mock_topics = [
            {"name": "quantum-computing", "page_count": 5},
            {"name": "machine-learning", "page_count": 3},
        ]

        with patch("sobriquets.api.routes.get_session_factory") as mock_sf, \
             patch("sobriquets.api.routes.list_topics", return_value=mock_topics):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_sf.return_value = MagicMock(return_value=mock_session)

            response = client.get("/api/topics")

        assert response.status_code == 200
        data = response.json()
        assert "topics" in data
        names = [t["name"] for t in data["topics"]]
        assert "quantum-computing" in names
        assert "machine-learning" in names

    def test_topics_empty_wiki_returns_empty_list(self, client: TestClient) -> None:
        with patch("sobriquets.api.routes.get_session_factory") as mock_sf, \
             patch("sobriquets.api.routes.list_topics", return_value=[]):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_sf.return_value = MagicMock(return_value=mock_session)

            response = client.get("/api/topics")

        assert response.status_code == 200
        assert response.json()["topics"] == []


# ---------------------------------------------------------------------------
# GET /api/pages/{topic}
# ---------------------------------------------------------------------------

class TestPagesEndpoint:
    def test_pages_returns_page_list(self, client: TestClient) -> None:
        mock_pages = [
            {"title": "Qubits Explained", "path": "quantum-computing/qubits.md"},
            {"title": "Overview", "path": "quantum-computing/overview.md"},
        ]

        with patch("sobriquets.api.routes.get_session_factory") as mock_sf, \
             patch("sobriquets.api.routes.list_pages_by_topic", return_value=mock_pages):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_sf.return_value = MagicMock(return_value=mock_session)

            response = client.get("/api/pages/quantum-computing")

        assert response.status_code == 200
        data = response.json()
        assert "pages" in data
        assert len(data["pages"]) == 2
        titles = [p["title"] for p in data["pages"]]
        assert "Qubits Explained" in titles

    def test_pages_unknown_topic_returns_empty_list(self, client: TestClient) -> None:
        with patch("sobriquets.api.routes.get_session_factory") as mock_sf, \
             patch("sobriquets.api.routes.list_pages_by_topic", return_value=[]):
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_sf.return_value = MagicMock(return_value=mock_session)

            response = client.get("/api/pages/nonexistent-topic")

        assert response.status_code == 200
        assert response.json()["pages"] == []


# ---------------------------------------------------------------------------
# _extract_sources helper
# ---------------------------------------------------------------------------

class TestExtractSources:
    def test_parses_single_source(self) -> None:
        from sobriquets.api.routes import _extract_sources

        tool_output = (
            "Source: Quantum Overview (quantum/overview.md)\n"
            "Section: Qubits\n"
            "Relevance: 0.920\n"
            "Content:\nQubits are the basic unit.\n"
        )
        sources = _extract_sources(tool_output)
        assert len(sources) == 1
        assert sources[0].title == "Quantum Overview"
        assert sources[0].file_path == "quantum/overview.md"
        assert sources[0].heading == "Qubits"
        assert abs(sources[0].relevance_score - 0.920) < 0.001

    def test_parses_multiple_sources(self) -> None:
        from sobriquets.api.routes import _extract_sources

        tool_output = (
            "Source: Page A (topic/a.md)\n"
            "Section: Intro\n"
            "Relevance: 0.85\n"
            "Content:\nContent A.\n"
            "---\n"
            "Source: Page B (topic/b.md)\n"
            "Section: Body\n"
            "Relevance: 0.72\n"
            "Content:\nContent B.\n"
        )
        sources = _extract_sources(tool_output)
        assert len(sources) == 2
        assert sources[0].title == "Page A"
        assert sources[1].title == "Page B"

    def test_no_source_markers_returns_empty(self) -> None:
        from sobriquets.api.routes import _extract_sources

        result = _extract_sources("No relevant results found in the knowledge base.")
        assert result == []

    def test_invalid_relevance_defaults_to_zero(self) -> None:
        from sobriquets.api.routes import _extract_sources

        tool_output = (
            "Source: Page (path.md)\n"
            "Relevance: not-a-number\n"
        )
        sources = _extract_sources(tool_output)
        assert len(sources) == 1
        assert sources[0].relevance_score == 0.0
