# ── Constants ──────────────────────────────────────────────────

MIN_CONTENT_LENGTH = 500
MIN_SPEC_KEYWORDS = 3

_ERROR_PATTERNS = [
    "access denied",
    "403 forbidden",
    "404 not found",
    "page not found",
    "checking your browser",
    "enable javascript",
    "reference #",
]

_SPEC_KEYWORDS = [
    "socket", "chipset", "ddr", "pcie", "memory",
    "form factor", "atx", "usb", "sata", "m.2",
    "dimm", "audio", "ethernet", "lan", "bios",
]


# ── Public API ─────────────────────────────────────────────────

def check_content(text: str) -> str | None:
    stripped = text.strip()
    error = looks_like_error_page(stripped)
    if error:
        return f"Error page detected ({error})"
    if len(stripped) < MIN_CONTENT_LENGTH:
        return f"Too little content ({len(stripped)} chars)"
    if not has_spec_content(stripped):
        return "No spec content detected"
    return None


# ── Helpers ────────────────────────────────────────────────────

def looks_like_error_page(text: str) -> str | None:
    lower = text.lower()
    for pattern in _ERROR_PATTERNS:
        if pattern in lower:
            return pattern
    return None


def has_spec_content(text: str) -> bool:
    lower = text.lower()
    hits = sum(1 for kw in _SPEC_KEYWORDS if kw in lower)
    return hits >= MIN_SPEC_KEYWORDS
