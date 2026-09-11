import hashlib
import json
from pathlib import Path


# ── Constants ──────────────────────────────────────────────────

_CACHE_DIR = Path(__file__).parent / "cache"

_enabled = True


# ── Public API ─────────────────────────────────────────────────

def disable():
    global _enabled
    _enabled = False


def get_page(url: str, rendered: bool) -> str | None:
    if not _enabled:
        return None
    path = _page_path(url, rendered)
    if path.exists():
        return path.read_text()
    return None


def set_page(url: str, rendered: bool, text: str):
    if not _enabled:
        return
    path = _page_path(url, rendered)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def get_extraction(prompt: str, schema: str, text: str) -> dict | None:
    if not _enabled:
        return None
    path = _extraction_path(prompt, schema, text)
    if path.exists():
        return json.loads(path.read_text())
    return None


def set_extraction(prompt: str, schema: str, text: str, result: dict):
    if not _enabled:
        return
    path = _extraction_path(prompt, schema, text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))


# ── Helpers ────────────────────────────────────────────────────

def _hash(*parts: str) -> str:
    combined = "\n---\n".join(parts)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def _page_path(url: str, rendered: bool) -> Path:
    key = _hash(url, str(rendered))
    return _CACHE_DIR / "pages" / f"{key}.txt"


def _extraction_path(prompt: str, schema: str, text: str) -> Path:
    key = _hash(prompt, schema, text)
    return _CACHE_DIR / "extractions" / f"{key}.json"
