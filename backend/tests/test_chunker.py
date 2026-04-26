"""Tests for sobriquets.ingest.chunker."""
import pytest

from sobriquets.ingest.chunker import (
    MAX_CHUNK_CHARS,
    MIN_CHUNK_CHARS,
    Chunk,
    chunk_markdown,
    _split_at_paragraphs,
    _split_by_headings,
    _merge_small_sections,
)


class TestChunkDataclass:
    def test_chunk_has_required_fields(self) -> None:
        c = Chunk(index=0, heading="Intro", content="Some text")
        assert c.index == 0
        assert c.heading == "Intro"
        assert c.content == "Some text"

    def test_chunk_heading_can_be_none(self) -> None:
        c = Chunk(index=0, heading=None, content="text")
        assert c.heading is None


class TestSplitByHeadings:
    def test_no_headings_returns_single_section(self) -> None:
        body = "Just plain text with no headings."
        sections = _split_by_headings(body)
        assert len(sections) == 1
        assert sections[0][0] is None
        assert "plain text" in sections[0][1]

    def test_h2_heading_splits_correctly(self) -> None:
        body = "## Section One\n\nContent of section one.\n\n## Section Two\n\nContent two."
        sections = _split_by_headings(body)
        # Should have two sections with headings
        headings = [h for h, _ in sections]
        assert "Section One" in headings
        assert "Section Two" in headings

    def test_h3_heading_nested_under_h2(self) -> None:
        body = "## Parent\n\nParent content.\n\n### Child\n\nChild content."
        sections = _split_by_headings(body)
        headings = [h for h, _ in sections]
        assert any("Parent > Child" in (h or "") for h in headings)

    def test_preamble_before_first_heading(self) -> None:
        body = "Introduction paragraph.\n\n## Section\n\nSection content."
        sections = _split_by_headings(body)
        # First item should be the preamble with None heading
        assert sections[0][0] is None
        assert "Introduction" in sections[0][1]

    def test_empty_body_returns_empty(self) -> None:
        assert _split_by_headings("") == []
        assert _split_by_headings("   \n  ") == []

    def test_h1_headings_are_not_split_points(self) -> None:
        """H1 headings should not trigger splits — only H2/H3 do."""
        body = "# Title\n\nSome content.\n\n# Another Title\n\nMore content."
        sections = _split_by_headings(body)
        # Both sections treated as single body (H1 not matched)
        assert len(sections) == 1


class TestMergeSmallSections:
    def test_empty_input_returns_empty(self) -> None:
        assert _merge_small_sections([]) == []

    def test_single_section_passes_through(self) -> None:
        sections = [("Heading", "A" * 200)]
        result = _merge_small_sections(sections)
        assert result == sections

    def test_small_section_merges_with_next(self) -> None:
        small = "Short."  # < MIN_CHUNK_CHARS
        big = "B" * 200
        sections = [("H1", small), ("H2", big)]
        result = _merge_small_sections(sections)
        # Should be merged into fewer sections
        total_content = "".join(c for _, c in result)
        assert "Short." in total_content
        assert "B" * 10 in total_content

    def test_large_sections_not_merged(self) -> None:
        s1 = "A" * 200
        s2 = "B" * 200
        sections = [("H1", s1), ("H2", s2)]
        result = _merge_small_sections(sections)
        assert len(result) == 2


class TestSplitAtParagraphs:
    def test_single_paragraph_under_max_returns_one_part(self) -> None:
        text = "Short paragraph."
        parts = _split_at_paragraphs(text, MAX_CHUNK_CHARS)
        assert len(parts) == 1
        assert parts[0] == text

    def test_splits_at_double_newline(self) -> None:
        para1 = "A" * 100
        para2 = "B" * 100
        text = para1 + "\n\n" + para2
        # Use small max to force split
        parts = _split_at_paragraphs(text, 150)
        assert len(parts) == 2
        assert para1 in parts[0]
        assert para2 in parts[1]

    def test_very_long_single_paragraph_stays_as_one(self) -> None:
        """If a single paragraph exceeds max_chars, it remains unsplit
        (no internal split point exists)."""
        text = "X" * (MAX_CHUNK_CHARS + 500)
        parts = _split_at_paragraphs(text, MAX_CHUNK_CHARS)
        assert len(parts) == 1


class TestChunkMarkdown:
    def test_empty_body_returns_empty_list(self) -> None:
        assert chunk_markdown("") == []
        assert chunk_markdown("   ") == []

    def test_plain_text_no_headings(self) -> None:
        body = "Just a paragraph of text with no headings at all."
        chunks = chunk_markdown(body)
        assert len(chunks) == 1
        assert chunks[0].heading is None
        assert "paragraph" in chunks[0].content

    def test_indices_are_sequential(self) -> None:
        body = "## Section One\n\nContent one.\n\n## Section Two\n\nContent two."
        chunks = chunk_markdown(body)
        indices = [c.index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_heading_based_splitting(self) -> None:
        # Each section must have content >= MIN_CHUNK_CHARS to avoid merging
        section_content = "W" * MIN_CHUNK_CHARS
        body = (
            f"## Alpha\n\n{section_content}\n\n"
            f"## Beta\n\n{section_content}\n\n"
            f"## Gamma\n\n{section_content}"
        )
        chunks = chunk_markdown(body)
        headings = [c.heading for c in chunks]
        assert "Alpha" in headings
        assert "Beta" in headings
        assert "Gamma" in headings

    def test_large_section_is_split(self) -> None:
        # Create a section that exceeds MAX_CHUNK_CHARS
        para = ("Word " * 50 + "\n\n") * 30  # ~7500 chars of paragraphs
        body = f"## Big Section\n\n{para}"
        chunks = chunk_markdown(body)
        # Should produce more than one chunk
        assert len(chunks) > 1
        # All chunks should be under or close to MAX_CHUNK_CHARS
        for c in chunks:
            assert len(c.content) <= MAX_CHUNK_CHARS + 500  # allow single-para overflow

    def test_returns_chunk_objects(self) -> None:
        body = "## Section\n\nContent here."
        chunks = chunk_markdown(body)
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_content_is_stripped(self) -> None:
        body = "## Section\n\n   Padded content.   \n"
        chunks = chunk_markdown(body)
        assert chunks[0].content == chunks[0].content.strip()

    def test_frontmatter_not_present_in_chunk_content(self) -> None:
        """The chunker receives the body (post frontmatter extraction),
        so frontmatter should not appear in chunks."""
        body = "## Real Content\n\nThis is the actual wiki content."
        chunks = chunk_markdown(body)
        for c in chunks:
            assert "---" not in c.content

    def test_nested_h3_heading_context(self) -> None:
        # Sections must be large enough to avoid merging (>= MIN_CHUNK_CHARS)
        parent_content = "P" * MIN_CHUNK_CHARS
        child_content = "C" * MIN_CHUNK_CHARS
        body = f"## Parent\n\n{parent_content}\n\n### Child\n\n{child_content}"
        chunks = chunk_markdown(body)
        child_chunk = next(
            (c for c in chunks if c.heading and "Child" in c.heading), None
        )
        assert child_chunk is not None
        assert "Parent" in child_chunk.heading

    def test_minimal_document(self) -> None:
        body = "x"
        chunks = chunk_markdown(body)
        # Either one chunk or empty (content too small but still a chunk)
        assert isinstance(chunks, list)
