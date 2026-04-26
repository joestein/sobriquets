"""Shared pytest fixtures for sobriquets tests."""
import asyncio
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Mock embedding provider
# ---------------------------------------------------------------------------

class MockEmbeddingProvider:
    """Returns fixed 384-dimension zero vectors for deterministic tests."""

    DIMENSION = 384

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * self.DIMENSION for _ in texts]


@pytest.fixture
def mock_embedding_provider() -> MockEmbeddingProvider:
    return MockEmbeddingProvider()


# ---------------------------------------------------------------------------
# Sample wiki markdown helpers
# ---------------------------------------------------------------------------

SAMPLE_FRONTMATTER_MD = """\
---
title: Quantum Computing Overview
topic: quantum-computing
tags: [quantum, overview]
---

## Introduction

Quantum computing leverages quantum mechanical phenomena like superposition and
entanglement to perform computations that classical computers cannot efficiently solve.

## Qubits

A qubit is the basic unit of quantum information. Unlike a classical bit that is
either 0 or 1, a qubit can exist in a superposition of both states simultaneously.

### Superposition

Superposition allows a quantum system to be in multiple states at once until
a measurement collapses it into a definite state.

### Entanglement

Entanglement is a phenomenon where two qubits become correlated such that the
state of one instantly influences the other, regardless of the distance between them.

## Quantum Gates

Quantum gates manipulate qubits analogously to classical logic gates.
"""

SAMPLE_MINIMAL_MD = """\
---
title: Minimal Page
topic: test
---

Short content.
"""

SAMPLE_NO_FRONTMATTER_MD = """\
## Just a heading

Some content without frontmatter.
"""

SAMPLE_LARGE_SECTION_MD = """\
---
title: Large Section Test
topic: test
---

## Big Section

""" + ("This is a paragraph of text. " * 20 + "\n\n") * 10


@pytest.fixture
def sample_wiki_dir(tmp_path: Path) -> Path:
    """Create a small wiki pages directory for lint/pipeline tests."""
    pages = tmp_path / "pages"
    pages.mkdir()
    raw_sources = tmp_path / "raw-sources"
    raw_sources.mkdir()

    # Topic directory
    topic_dir = pages / "quantum-computing"
    topic_dir.mkdir()

    (topic_dir / "overview.md").write_text(
        SAMPLE_FRONTMATTER_MD, encoding="utf-8"
    )

    # A page that references overview.md
    (topic_dir / "qubits.md").write_text(
        """\
---
title: Qubits Explained
topic: quantum-computing
---

Qubits are the foundation.
See [[quantum-computing/overview.md]] for background.
""",
        encoding="utf-8",
    )

    return tmp_path


@pytest.fixture
def pages_dir(sample_wiki_dir: Path) -> Path:
    return sample_wiki_dir / "pages"


@pytest.fixture
def raw_sources_dir(sample_wiki_dir: Path) -> Path:
    return sample_wiki_dir / "raw-sources"
