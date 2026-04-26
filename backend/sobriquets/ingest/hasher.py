import hashlib
from pathlib import Path


def hash_file(file_path: Path) -> str:
    """Compute SHA-256 hash of a file's content."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
