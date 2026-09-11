import argparse
import json

from fetcher import search, fetch_text, fetch_rendered, url_variants
from extractor import extract
from schemas import Motherboard


# ── Constants ──────────────────────────────────────────────────

MIN_CONTENT_LENGTH = 500
MIN_SPEC_KEYWORDS = 3
MAX_SOURCES = 3

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

def main():
    parser = argparse.ArgumentParser(description="Extract motherboard specs using LLM")
    parser.add_argument("query", help="Motherboard name or URL")
    parser.add_argument(
        "--url", action="store_true", help="Treat query as a URL instead of a search term"
    )
    parser.add_argument(
        "--result", type=int, default=None, help="Use a specific search result (1-10). Omit to auto-try all."
    )
    parser.add_argument(
        "--rendered", action="store_true", help="Use Playwright to render JS before extracting"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print extracted text instead of sending to LLM"
    )
    args = parser.parse_args()

    if args.url:
        url = args.query
        print(f"Fetching: {url}")
        text = _fetch(url, args.rendered)
        _print_or_extract(text, args.debug)
        return

    print(f"Searching for: {args.query}")
    urls = search(args.query)

    if args.result is not None:
        idx = args.result - 1
        if idx < 0 or idx >= len(urls):
            print(f"Only {len(urls)} results found, asked for #{args.result}")
            return
        url = urls[idx]
        print(f"Using: {url}")
        text = _fetch(url, args.rendered)
        _print_or_extract(text, args.debug)
        return

    print("Auto-trying results...")
    if args.debug:
        _debug_candidates(urls, args.rendered)
    else:
        _extract_with_gap_fill(urls, args.rendered)


# ── Core logic ─────────────────────────────────────────────────

def _extract_with_gap_fill(urls: list[str], rendered: bool):
    candidates = _fetch_candidates(urls, rendered)
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

        gaps = _has_gaps(board)
        if not gaps:
            print("  All fields filled.")
            break
        print(f"  Gaps: {', '.join(gaps)}")

    if not boards:
        print("All results failed — no usable content found.")
        return

    if len(boards) > 1:
        result = _merge(boards)
        remaining = _has_gaps(result)
        if remaining:
            print(f"After merge, still missing: {', '.join(remaining)}")
        else:
            print("Merge filled all gaps.")
    else:
        result = boards[0]

    print(f"\nSources used: {len(sources)}")
    for i, src in enumerate(sources):
        print(f"  [{i + 1}] {src}")

    print("\n" + json.dumps(result.model_dump(), indent=2))
    print(f"\nTokens — input: {total_input}, output: {total_output}")


def _fetch_candidates(urls: list[str], rendered: bool):
    for i, url in enumerate(urls):
        for variant in url_variants(url):
            suffix = " (fixed encoding)" if variant != url else ""
            try:
                print(f"  Trying [{i + 1}]: {variant}{suffix}")
                text = _fetch(variant, rendered)
                stripped = text.strip()
                if _looks_like_error_page(stripped):
                    match = next(p for p in _ERROR_PATTERNS if p in stripped.lower())
                    print(f"    Error page detected ({match}), skipping")
                    continue
                if len(stripped) < MIN_CONTENT_LENGTH:
                    print(f"    Too little content ({len(stripped)} chars), skipping")
                    continue
                if not _has_spec_content(stripped):
                    print(f"    No spec content detected, skipping")
                    continue
                yield variant, text
            except Exception as e:
                print(f"    Failed: {e}")
                continue


def fetch_with_fallback(urls: list[str], rendered: bool) -> tuple[str, str]:
    for url, text in _fetch_candidates(urls, rendered):
        return url, text
    raise ValueError(f"All {len(urls)} results failed")


# ── Helpers ────────────────────────────────────────────────────

def _fetch(url: str, rendered: bool) -> str:
    if rendered:
        return fetch_rendered(url)
    return fetch_text(url)


def _print_or_extract(text: str, debug: bool):
    if debug:
        print(f"\n--- Extracted text ({len(text)} chars) ---")
        print(text[:2000])
        if len(text) > 2000:
            print(f"\n... ({len(text) - 2000} more chars)")
        return

    print("Extracting specs...")
    board, usage = extract(text)
    print("\n" + json.dumps(board.model_dump(), indent=2))
    print(f"\nTokens — input: {usage.input_tokens}, output: {usage.output_tokens}")


def _debug_candidates(urls: list[str], rendered: bool):
    count = 0
    for url, text in _fetch_candidates(urls, rendered):
        if count >= MAX_SOURCES:
            break
        count += 1
        print(f"\n--- [{count}] Extracted text from {url} ({len(text)} chars) ---")
        print(text[:2000])
        if len(text) > 2000:
            print(f"\n... ({len(text) - 2000} more chars)")


def _looks_like_error_page(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in _ERROR_PATTERNS)


def _has_spec_content(text: str) -> bool:
    lower = text.lower()
    hits = sum(1 for kw in _SPEC_KEYWORDS if kw in lower)
    return hits >= MIN_SPEC_KEYWORDS


def _has_gaps(board: Motherboard) -> list[str]:
    gaps = []
    for key, val in board.model_dump().items():
        if val is None or val == []:
            gaps.append(key)
    return gaps


def _merge(boards: list[Motherboard]) -> Motherboard:
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


if __name__ == "__main__":
    main()
