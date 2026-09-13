# Pilot — Motherboard Spec Extractor

An LLM-powered tool that searches for motherboard specification pages, extracts structured data using Claude, and merges results from multiple sources to fill gaps.

## How It Works

1. **Search** — Queries DuckDuckGo for the board name, returns up to 10 results ranked by relevance and manufacturer priority.
2. **Fetch** — Tries each URL through a fallback chain, filtering out error pages, empty shells, and pages with no spec content.
3. **Extract** — Sends the page text to Claude Haiku with a tuned system prompt and Pydantic schema. Returns structured JSON.
4. **Gap Fill** — If the first extraction has null fields or empty lists, fetches and extracts from additional sources (up to 3 total), then merges the results.

## Architecture

```
cli.py           — CLI entry point, argument parsing, orchestration
fetcher.py       — DuckDuckGo search, HTTP fetching, Playwright rendering
validator.py     — Content validation (error pages, length, spec keywords)
extractor.py     — LLM extraction via Claude Haiku, JSON parsing
spec_merger.py   — Multi-source gap filling, list deduplication, merge logic
schemas.py       — Pydantic models for motherboard specs
cache.py         — File-based caching for pages and LLM extractions
evals/eval.py    — Evaluation framework comparing extraction against ground truth
```

## Key Engineering Decisions

### Search & Ranking

- **Manufacturer URL priority**: URLs from known manufacturers (ASUS, Gigabyte, MSI, ASRock, etc.) sort to the top of search results, since they're the most authoritative source.
- **Relevance scoring**: Each URL is scored by how many query terms appear in the URL path (2 points each) and DuckDuckGo title (1 point each). This prevents similar board names from being confused — e.g., "X870 AORUS STEALTH ICE" ranks above "X870 AORUS STEALTH" when searching for the ICE variant.
- **10 results**: DuckDuckGo returns unstable results and many sites block automated requests, so a larger pool gives the fallback chain more to work with.

### Fetching & Validation

- **URL encoding fix**: DuckDuckGo puts `+` in URL paths where `%20` belongs. Since `+` only means space in query strings (not paths), the tool generates a `%20` variant for any URL with `+` in its path and tries both.
- **Three-layer content validation** (in `validator.py`):
  - **Error page detection**: Checks for patterns like "access denied", "403 forbidden", "enable javascript". These are typically WAF blocks (Akamai, Cloudflare) that return HTML pages passing length checks.
  - **Minimum content length** (500 chars): Pages under this threshold are usually empty shells or redirects.
  - **Spec keyword check**: Requires at least 3 motherboard-related terms (socket, chipset, DDR, PCIe, etc.). Catches pages that pass length checks but contain only navigation chrome with no actual spec data.
- **Playwright rendering**: The `--rendered` flag launches headless Chromium for JavaScript-heavy pages. Automatically clicks spec/specification tabs using common label patterns.

### Extraction

- **Claude Haiku**: Chosen for cost and speed — spec extraction is a structured task that doesn't need a larger model.
- **Tuned system prompt**: Field-level guidance for each complex field, developed iteratively from real extraction failures:
  - PCIe slots: Distinguishes physical slot size from electrical bandwidth mode (e.g., "PCIe 4.0 x16 (x4 mode)").
  - M.2 slots: Requires verbal generation format ("Gen5x4" not "PCIe 5.0 x4") and form factor. Prefers 2280 when multiple sizes are supported.
  - USB/Audio: Separates rear panel ports from front panel (internal header) ports.
  - WiFi/Bluetooth: Three-state enum — "built-in", "optional module" (has a Key E slot but no card), or "none".
- **Nullable core fields**: Fields like name, chipset, and socket accept null so partial extraction returns usable data instead of crashing.
- **JSON recovery**: The LLM sometimes wraps JSON in markdown fences or includes preamble text. The parser strips fences and falls back to finding the first `{...}` block.

### Gap Filling & Merge

- **Conditional multi-source**: Only fetches additional pages when the first extraction has gaps (null fields or empty lists). If the first source is complete, no extra LLM calls are made.
- **Maximum 3 sources**: Caps token spend. Each additional source is a full LLM extraction call.
- **List union with exact-match dedup**: Instead of taking the longer list, unions entries from all sources. Deduplicates using the same key tuples as the eval framework — `(location, type, quantity)` for USB/audio, `(type, quantity)` for PCIe/M.2/video.
- **"none" overwrite**: String fields with the value "none" (like `wifi_bluetooth`) are treated as gaps during merge. If a later source finds "built-in" or "optional module", it overwrites the "none".
- **Scalar preference**: For non-list fields, takes the first non-null value across sources.

### Caching

- **Two-layer file cache**: Pages and LLM extractions are cached separately under `cache/`. Both the CLI and eval framework benefit automatically since they go through the same `fetcher.py` and `extractor.py` code paths.
- **Page cache**: Keyed by URL + rendered flag. Eliminates redundant network requests when re-running on the same board or re-running evals.
- **Extraction cache**: Keyed by a hash of (system prompt + schema + page text). Automatically invalidates when you change the prompt or schema, but hits when only eval logic or ground truth changes.
- **`--no-cache` flag**: Bypasses both caches for a fresh run without clearing stored entries.
- **`--clear-cache` flag**: Wipes all cached pages and extractions. Can run standalone or before a query.

### Logging

- **Named logger, no `basicConfig()`**: All modules log through `logging.getLogger("pilot")`. The handler is configured only in entry points (`cli.py`, `evals/eval.py`) — never via `basicConfig()`. This is deliberate: `basicConfig()` attaches a handler to the root logger, which causes every third-party library using Python's logging (urllib3, httpx, the Anthropic SDK, ddgs) to emit its own messages through your handler. A named logger avoids this entirely — third-party loggers stay silent because the root logger has no handler.
- **Log levels**: `info` for normal operational output, `warning` for recoverable issues (content validation skips, incomplete data after merge), `error` for failures (fetch exceptions, unparseable LLM responses, cache write errors).
- **`%(message)s` format**: Output looks identical to plain `print()` — no timestamps or level prefixes. The structure is there for programmatic filtering if needed later.

### Evaluation

- **Ground truth files**: Hand-verified JSON specs per board stored in `evals/ground_truth/`.
- **Field-level scoring**: Each field is compared individually. List fields use set comparison on their key tuples (order-independent). Scalar fields use exact match.
- **Skip unfilled**: Ground truth templates with empty fields are skipped rather than scored, so partially filled templates don't produce misleading scores.

## Usage

```bash
# Search and extract (auto-fallback through results)
python cli.py "ASUS ROG STRIX Z790-E Gaming WiFi"

# Use Playwright for JS-heavy pages
python cli.py --rendered "GIGABYTE X870 AORUS STEALTH ICE"

# Extract from a specific URL
python cli.py --url "https://example.com/motherboard/specs"

# Pick a specific search result
python cli.py --result 3 "MSI MEG X870E ACE MAX"

# Debug: see fetched text without sending to LLM
python cli.py --debug "ASRock X670E PG Lightning"

# Bypass cache for a fresh fetch + extraction
python cli.py --no-cache "ASUS ROG STRIX Z790-E Gaming WiFi"

# Clear all cached pages and extractions
python cli.py --clear-cache

# Clear cache, then run a fresh query
python cli.py --clear-cache "ASUS ROG STRIX Z790-E Gaming WiFi"

# Run evaluation against ground truth
python evals/eval.py
```

## Setup

```bash
pip install .
playwright install chromium
```

Requires an `ANTHROPIC_API_KEY` environment variable.
