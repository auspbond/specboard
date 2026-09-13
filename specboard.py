import argparse
import json
import logging
import sys

import cache
from comparator import compare
from fetcher import search, fetch_text, fetch_rendered, url_variants
from extractor import extract
from spec_merger import extract_with_gap_fill, MAX_SOURCES
from validator import check_content

log = logging.getLogger("specboard")
log.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))
log.addHandler(_handler)


# ── Public API ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extract motherboard specs using LLM")
    parser.add_argument("query", nargs="?", help="Motherboard name or URL")
    parser.add_argument(
        "--url", action="store_true", help="Treat query as a URL instead of a search term"
    )
    parser.add_argument(
        "--result", type=int, default=None, help="Use a specific search result (1-10). Omit to auto-try all."
    )
    parser.add_argument(
        "--compare", nargs=2, metavar="BOARD", help="Compare two boards side by side"
    )
    parser.add_argument(
        "--rendered", action="store_true", help="Use Playwright to render JS before extracting"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print extracted text instead of sending to LLM"
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Bypass page and extraction cache"
    )
    parser.add_argument(
        "--clear-cache", action="store_true", help="Clear all cached pages and extractions"
    )
    args = parser.parse_args()

    if args.clear_cache:
        cache.clear()
        if not args.query:
            return

    if args.no_cache:
        cache.disable()

    if args.compare:
        _run_compare(args.compare[0], args.compare[1], args.rendered)
        return

    if not args.query:
        parser.error("query is required (unless using --clear-cache or --compare)")

    if args.url:
        url = args.query
        log.info("Fetching: %s", url)
        text = _fetch(url, args.rendered)
        _print_or_extract(text, args.debug)
        return

    log.info("Searching for: %s", args.query)
    urls = search(args.query)

    if args.result is not None:
        idx = args.result - 1
        if idx < 0 or idx >= len(urls):
            log.warning("Only %d results found, asked for #%d", len(urls), args.result)
            return
        url = urls[idx]
        log.info("Using: %s", url)
        text = _fetch(url, args.rendered)
        _print_or_extract(text, args.debug)
        return

    log.info("Auto-trying results...")
    if args.debug:
        _debug_candidates(urls, args.rendered)
    else:
        candidates = _fetch_candidates(urls, args.rendered)
        result = extract_with_gap_fill(candidates, args.rendered)
        if not result:
            log.error("All results failed — no usable content found.")
            return

        board, sources, total_input, total_output = result

        log.info("\nSources used: %d", len(sources))
        for i, src in enumerate(sources):
            log.info("  [%d] %s", i + 1, src)

        log.info("\n%s", json.dumps(board.model_dump(), indent=2))
        log.info("\nTokens — input: %d, output: %d", total_input, total_output)


# ── Core logic ─────────────────────────────────────────────────

def _fetch_candidates(urls: list[str], rendered: bool):
    for i, url in enumerate(urls):
        for variant in url_variants(url):
            suffix = " (fixed encoding)" if variant != url else ""
            try:
                log.info("  Trying [%d]: %s%s", i + 1, variant, suffix)
                text = _fetch(variant, rendered)
                reason = check_content(text)
                if reason:
                    log.warning("    %s, skipping", reason)
                    continue
                yield variant, text
            except Exception as e:
                log.error("    Failed: %s", e)
                continue


def fetch_with_fallback(urls: list[str], rendered: bool) -> tuple[str, str]:
    for url, text in _fetch_candidates(urls, rendered):
        return url, text
    raise ValueError(f"All {len(urls)} results failed")


def _extract_board(query: str, rendered: bool):
    log.info("Searching for: %s", query)
    urls = search(query)
    log.info("Auto-trying results...")
    candidates = _fetch_candidates(urls, rendered)
    result = extract_with_gap_fill(candidates, rendered)
    if not result:
        log.error("All results failed for: %s", query)
        return None
    board, sources, total_input, total_output = result
    log.info("  Sources: %d, tokens: %d in / %d out",
             len(sources), total_input, total_output)
    return board


def _run_compare(query_a: str, query_b: str, rendered: bool):
    log.info("=== Extracting board 1 ===")
    board_a = _extract_board(query_a, rendered)
    if not board_a:
        return

    log.info("\n=== Extracting board 2 ===")
    board_b = _extract_board(query_b, rendered)
    if not board_b:
        return

    log.info("\n=== Comparison ===")
    compare(board_a, board_b)


# ── Helpers ────────────────────────────────────────────────────

def _fetch(url: str, rendered: bool) -> str:
    if rendered:
        return fetch_rendered(url)
    return fetch_text(url)


def _print_or_extract(text: str, debug: bool):
    if debug:
        log.info("\n--- Extracted text (%d chars) ---", len(text))
        log.info(text[:2000])
        if len(text) > 2000:
            log.info("\n... (%d more chars)", len(text) - 2000)
        return

    log.info("Extracting specs...")
    board, usage = extract(text)
    log.info("\n%s", json.dumps(board.model_dump(), indent=2))
    log.info("\nTokens — input: %d, output: %d", usage.input_tokens, usage.output_tokens)


def _debug_candidates(urls: list[str], rendered: bool):
    count = 0
    for url, text in _fetch_candidates(urls, rendered):
        if count >= MAX_SOURCES:
            break
        count += 1
        log.info("\n--- [%d] Extracted text from %s (%d chars) ---", count, url, len(text))
        log.info(text[:2000])
        if len(text) > 2000:
            log.info("\n... (%d more chars)", len(text) - 2000)


if __name__ == "__main__":
    main()
