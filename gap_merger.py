from extractor import extract
from schemas import Motherboard


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

        print(f"Extracting from: {url} ({len(boards) + 1}/{MAX_SOURCES})")
        board, usage = extract(text)
        boards.append(board)
        sources.append(url)
        total_input += usage.input_tokens
        total_output += usage.output_tokens

        gaps = has_gaps(board)
        if not gaps:
            print("  All fields filled.")
            break
        print(f"  Gaps: {', '.join(gaps)}")

    if not boards:
        return None

    if len(boards) > 1:
        result = merge(boards)
        remaining = has_gaps(result)
        if remaining:
            print(f"After merge, still missing: {', '.join(remaining)}")
        else:
            print("Merge filled all gaps.")
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
                if len(val) > len(current):
                    merged[key] = val
            elif current is None and val is not None:
                merged[key] = val
    return Motherboard(**merged)
