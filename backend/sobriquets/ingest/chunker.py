import re
from dataclasses import dataclass


@dataclass
class Chunk:
    """A chunk of wiki content with its heading context."""

    index: int
    heading: str | None
    content: str


# Approximate max chars per chunk (roughly 1000 tokens)
MAX_CHUNK_CHARS = 4000
# Minimum chars for a standalone chunk
MIN_CHUNK_CHARS = 100


def chunk_markdown(body: str) -> list[Chunk]:
    """Split markdown body into chunks based on H2/H3 headings.

    Strategy:
    - Split on H2 and H3 headings
    - Each section becomes a chunk with its heading as context
    - Sections exceeding MAX_CHUNK_CHARS are split at paragraph boundaries
    - Sections shorter than MIN_CHUNK_CHARS are merged with the next section
    """
    sections = _split_by_headings(body)

    if not sections:
        if body.strip():
            return [Chunk(index=0, heading=None, content=body.strip())]
        return []

    # Merge small sections with the next one
    merged = _merge_small_sections(sections)

    # Split large sections at paragraph boundaries
    final: list[tuple[str | None, str]] = []
    for heading, content in merged:
        if len(content) > MAX_CHUNK_CHARS:
            parts = _split_at_paragraphs(content, MAX_CHUNK_CHARS)
            for part in parts:
                final.append((heading, part))
        else:
            final.append((heading, content))

    return [
        Chunk(index=i, heading=heading, content=content.strip())
        for i, (heading, content) in enumerate(final)
        if content.strip()
    ]


def _split_by_headings(body: str) -> list[tuple[str | None, str]]:
    """Split markdown by H2/H3 headings into (heading, content) pairs."""
    pattern = re.compile(r"^(#{2,3})\s+(.+)$", re.MULTILINE)

    sections: list[tuple[str | None, str]] = []
    last_end = 0
    current_heading_stack: list[str] = []

    matches = list(pattern.finditer(body))

    # Content before the first heading
    if matches:
        preamble = body[: matches[0].start()].strip()
        if preamble:
            sections.append((None, preamble))
    elif body.strip():
        return [(None, body.strip())]

    for i, match in enumerate(matches):
        level = len(match.group(1))
        heading_text = match.group(2).strip()

        if level == 2:
            current_heading_stack = [heading_text]
        elif level == 3:
            if current_heading_stack:
                current_heading_stack = [current_heading_stack[0], heading_text]
            else:
                current_heading_stack = [heading_text]

        # Get content from after this heading to the next heading
        content_start = match.end()
        if i + 1 < len(matches):
            content_end = matches[i + 1].start()
        else:
            content_end = len(body)

        content = body[content_start:content_end].strip()
        heading_str = " > ".join(current_heading_stack)
        sections.append((heading_str, content))

    return sections


def _merge_small_sections(
    sections: list[tuple[str | None, str]],
) -> list[tuple[str | None, str]]:
    """Merge sections shorter than MIN_CHUNK_CHARS with the next section."""
    if not sections:
        return []

    merged: list[tuple[str | None, str]] = []
    pending_heading: str | None = None
    pending_content = ""

    for heading, content in sections:
        if pending_content and len(pending_content) < MIN_CHUNK_CHARS:
            # Merge with current section
            pending_content += "\n\n" + content
            if heading and not pending_heading:
                pending_heading = heading
        else:
            if pending_content:
                merged.append((pending_heading, pending_content))
            pending_heading = heading
            pending_content = content

    if pending_content:
        merged.append((pending_heading, pending_content))

    return merged


def _split_at_paragraphs(text: str, max_chars: int) -> list[str]:
    """Split text at paragraph boundaries to keep under max_chars."""
    paragraphs = re.split(r"\n\n+", text)
    parts: list[str] = []
    current = ""

    for para in paragraphs:
        if current and len(current) + len(para) + 2 > max_chars:
            parts.append(current.strip())
            current = para
        else:
            current = current + "\n\n" + para if current else para

    if current.strip():
        parts.append(current.strip())

    return parts
