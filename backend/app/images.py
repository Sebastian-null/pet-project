import secrets
from pathlib import Path

from .config import settings

TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_BYTES = 4 * 1024 * 1024


def detect(content: bytes) -> str | None:
    """Read the real image type from the file itself — what the client claims is not trusted."""
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


async def read_capped(file) -> bytes | None:
    """Read an upload in chunks, returning None as soon as it passes MAX_BYTES.

    The Content-Length guard in main.py only sees what the client declares, and a
    chunked upload declares nothing at all — so the real limit is enforced here,
    while reading, instead of pulling an arbitrarily large body into memory first.
    """
    chunks, total = [], 0
    while chunk := await file.read(64 * 1024):
        total += len(chunk)
        if total > MAX_BYTES:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


def store(content: bytes, prefix: str, extension: str) -> str:
    """Save an upload under the media folder and return the path the API serves it at."""
    directory = Path(settings.media_dir)
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{prefix}-{secrets.token_hex(8)}{extension}"
    (directory / name).write_bytes(content)
    return f"/media/{name}"


def remove(url: str | None) -> None:
    if not url or not url.startswith("/media/"):
        return
    path = Path(settings.media_dir) / Path(url).name
    if path.exists():
        path.unlink()
