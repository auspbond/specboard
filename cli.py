import argparse
import json

from fetcher import search, fetch_text, fetch_rendered
from extractor import extract


def main():
    parser = argparse.ArgumentParser(description="Extract motherboard specs using LLM")
    parser.add_argument("query", help="Motherboard name or URL")
    parser.add_argument(
        "--url", action="store_true", help="Treat query as a URL instead of a search term"
    )
    parser.add_argument(
        "--result", type=int, default=1, help="Which search result to use (default: 1)"
    )
    parser.add_argument(
        "--rendered", action="store_true", help="Use Playwright to render JS before extracting"
    )
    args = parser.parse_args()

    if args.url:
        url = args.query
    else:
        print(f"Searching for: {args.query}")
        url = search(args.query, result_index=args.result - 1)
        print(f"Using: {url}")

    if args.rendered:
        print("Fetching page (rendered)...")
        text = fetch_rendered(url)
    else:
        print("Fetching page...")
        text = fetch_text(url)

    print("Extracting specs...")
    board, usage = extract(text)

    print("\n" + json.dumps(board.model_dump(), indent=2))
    print(f"\nTokens — input: {usage.input_tokens}, output: {usage.output_tokens}")


if __name__ == "__main__":
    main()
