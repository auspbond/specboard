import logging

from extractor import extract
from schemas import Motherboard

logger = logging.getLogger(__name__)


# ── Constants ──────────────────────────────────────────────────

MAX_SOURCES = 3


# ── Public API ─────────────────────────────────────────────────

def extract_with_gap_fill(candidates, rendered: bool) -> tuple[Motherboard, list[str], int, int] | None:
    boards = []
    sources = []
    total_input = 0
    total_output = 0

    for url, text in candidates:
        if len(boards) >= MAX_SOURCES:
            break

        logger.info("Extracting from: %s (%d/%d)", url, len(boards) + 1, MAX_SOURCES)
        board, usage = extract(text)
        boards.append(board)
        sources.append(url)
        total_input += usage.input_tokens
        total_output += usage.output_tokens

        gaps = has_gaps(board)
        if not gaps:
            logger.info("  All fields filled.")
            break
        logger.info("  Gaps: %s", ", ".join(gaps))

    if not boards:
        return None

    if len(boards) > 1:
        result = merge(boards)
        remaining = has_gaps(result)
        if remaining:
            logger.warning("After merge, still missing: %s", ", ".join(remaining))
        else:
            logger.info("Merge filled all gaps.")
    else:
        result = boards[0]

    return result, sources, total_input, total_output


# ── Helpers ────────────────────────────────────────────────────

def has_gaps(board: Motherboard) -> list[str]:
    gaps = []
    for key, val in board.model_dump().items():
        if val is None or val == []:
            gaps.append(key)
    return gaps


def merge(boards: list[Motherboard]) -> Motherboard:
    merged = boards[0].model_dump()
    for board in boards[1:]:
        for key, val in board.model_dump().items():
            current = merged[key]
            if isinstance(current, list) and isinstance(val, list):
                merged[key] = _union_lists(key, current, val)
            elif current is None and val is not None:
                merged[key] = val
            elif current == "none" and val not in (None, "none"):
                merged[key] = val
    return Motherboard(**merged)


_LOCATION_KEYED = {"usb_ports", "audio_jacks"}
_TYPE_KEYED = {"pcie_slots", "m2_slots", "video_ports"}


def _entry_key(field: str, entry: dict) -> tuple:
    if field in _LOCATION_KEYED:
        return (entry["location"], entry["type"], entry["quantity"])
    if field in _TYPE_KEYED:
        return (entry["type"], entry["quantity"])
    return tuple(sorted(entry.items()))


def _union_lists(field: str, base: list[dict], other: list[dict]) -> list[dict]:
    seen = {_entry_key(field, e) for e in base}
    result = list(base)
    for entry in other:
        if _entry_key(field, entry) not in seen:
            result.append(entry)
            seen.add(_entry_key(field, entry))
    return result
