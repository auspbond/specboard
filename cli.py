import argparse
import json

from fetcher import search, fetch_text, fetch_rendered, url_variants
from extractor import extract

MIN_CONTENT_LENGTH = 500

_ERROR_PATTERNS = [
    "access denied",
    "403 forbidden",
    "404 not found",
    "page not found",
    "checking your browser",
    "enable javascript",
    "reference #",
]


def _looks_like_error_page(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in _ERROR_PATTERNS)


def _fetch(url: str, rendered: bool) -> str:
    if rendered:
        return fetch_rendered(url)
    return fetch_text(url)


def _fetch_with_fallback(urls: list[str], rendered: bool) -> tuple[str, str]:
    last_error = None
    for i, url in enumerate(urls):
        for variant in url_variants(url):
            suffix = " (fixed encoding)" if variant != url else ""
            try:
                print(f"  Trying [{i + 1}]: {variant}{suffix}")
                text = _fetch(variant, rendered)
                stripped = text.strip()
                if len(stripped) < MIN_CONTENT_LENGTH:
                    print(f"    Too little content ({len(stripped)} chars), skipping")
                    continue
                if _looks_like_error_page(stripped):
                    print(f"    Looks like an error page, skipping")
                    continue
                return variant, text
            except Exception as e:
                print(f"    Failed: {e}")
                last_error = e
                continue
    raise ValueError(f"All {len(urls)} results failed. Last error: {last_error}")


def main():
    parser = argparse.ArgumentParser(description="Extract motherboard specs using LLM")
    parser.add_argument("query", help="Motherboard name or URL")
    parser.add_argument(
        "--url", action="store_true", help="Treat query as a URL instead of a search term"
    )
    parser.add_argument(
        "--result", type=int, default=None, help="Use a specific search result (1-5). Omit to auto-try all."
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
    else:
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
        else:
            print("Auto-trying results...")
            url, text = _fetch_with_fallback(urls, args.rendered)
            print(f"Using: {url}")

    if args.debug:
        print(f"\n--- Extracted text ({len(text)} chars) ---")
        print(text[:2000])
        if len(text) > 2000:
            print(f"\n... ({len(text) - 2000} more chars)")
        return

    print("Extracting specs...")
    board, usage = extract(text)

    print("\n" + json.dumps(board.model_dump(), indent=2))
    print(f"\nTokens — input: {usage.input_tokens}, output: {usage.output_tokens}")


if __name__ == "__main__":
    main()
