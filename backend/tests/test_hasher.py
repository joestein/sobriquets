"""Tests for sobriquets.ingest.hasher."""
from pathlib import Path

import pytest

from sobriquets.ingest.hasher import hash_file


class TestHashFile:
    def test_returns_hex_string(self, tmp_path: Path) -> None:
        f = tmp_path / "test.md"
        f.write_bytes(b"hello world")
        result = hash_file(f)
        assert isinstance(result, str)
        # SHA-256 hex digest is always 64 characters
        assert len(result) == 64

    def test_known_hash(self, tmp_path: Path) -> None:
        """SHA-256 of b'hello world' is a well-known constant."""
        f = tmp_path / "test.md"
        f.write_bytes(b"hello world")
        expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe04294e576f4b2b4b9d948d2f5"
        # Compute the real known hash inline to avoid hardcoding errors
        import hashlib
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert hash_file(f) == expected

    def test_different_content_produces_different_hashes(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.md"
        f2 = tmp_path / "b.md"
        f1.write_bytes(b"content A")
        f2.write_bytes(b"content B")
        assert hash_file(f1) != hash_file(f2)

    def test_same_content_produces_same_hash(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.md"
        f2 = tmp_path / "b.md"
        content = b"identical content"
        f1.write_bytes(content)
        f2.write_bytes(content)
        assert hash_file(f1) == hash_file(f2)

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.md"
        f.write_bytes(b"")
        result = hash_file(f)
        import hashlib
        assert result == hashlib.sha256(b"").hexdigest()

    def test_large_file_chunked_reading(self, tmp_path: Path) -> None:
        """Ensures chunked reading (>8192 bytes) produces correct hash."""
        import hashlib
        content = b"x" * 100_000  # 100 KB — triggers multiple read chunks
        f = tmp_path / "large.md"
        f.write_bytes(content)
        assert hash_file(f) == hashlib.sha256(content).hexdigest()

    def test_binary_content(self, tmp_path: Path) -> None:
        import hashlib
        content = bytes(range(256))
        f = tmp_path / "binary.bin"
        f.write_bytes(content)
        assert hash_file(f) == hashlib.sha256(content).hexdigest()
