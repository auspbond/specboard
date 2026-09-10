import argparse
import json

from fetcher import search, fetch_text
from extractor import extract


def main():
    parser = argparse.ArgumentParser(description="Extract motherboard specs using LLM")
    parser.add_argument("query", help="Motherboard name or URL")
    parser.add_argument(
        "--url", action="store_true", help="Treat query as a URL instead of a search term"
    )
    args = parser.parse_args()

    if args.url:
        url = args.query
    else:
        print(f"Searching for: {args.query}")
        url = search(args.query)
        print(f"Found: {url}")

    print("Fetching page...")
    text = fetch_text(url)

    print("Extracting specs...")
    board, usage = extract(text)

    print("\n" + json.dumps(board.model_dump(), indent=2))
    print(f"\nTokens — input: {usage.input_tokens}, output: {usage.output_tokens}")


if __name__ == "__main__":
    main()
