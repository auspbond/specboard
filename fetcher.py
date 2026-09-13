import logging
import re
from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

import cache

log = logging.getLogger("pilot")


# ── Constants ──────────────────────────────────────────────────

_MANUFACTURERS = [
    "asrock",
    "asus",
    "biostar",
    "evga",
    "gigabyte",
    "msi",
    "nzxt",
    "supermicro",
]

_SPEC_TAB_PATTERNS = [
    "Specification",
    "Specifications",
    "Specs",
    "Tech Specs",
    "Technical Specifications",
    "Features & Specifications",
]


# ── Public API ─────────────────────────────────────────────────

def search(query: str) -> list[str]:
    with DDGS() as ddgs:
        results = list(ddgs.text(f"{query} motherboard specifications", max_results=10))
    if not results:
        raise ValueError(f"No results found for: {query}")

    terms = _query_terms(query)

    scored = []
    for r in results:
        url = r["href"]
        title = r.get("title", "")
        mfr = _is_manufacturer_url(url)
        relevance = _relevance_score(terms, url, title)
        scored.append((mfr, relevance, url))

    scored.sort(key=lambda x: (not x[0], -x[1]))

    urls = [url for _, _, url in scored]
    for i, (mfr, relevance, url) in enumerate(scored):
        tag = " (manufacturer)" if mfr else ""
        log.info("  [%d] %s%s (score: %d)", i + 1, url, tag, relevance)
    return urls


def fetch_text(url: str) -> str:
    cached = cache.get_page(url, rendered=False)
    if cached is not None:
        log.info("    (cached page)")
        return cached
    response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    text = _strip_html(response.text)
    cache.set_page(url, rendered=False, text=text)
    return text


def fetch_rendered(url: str) -> str:
    cached = cache.get_page(url, rendered=True)
    if cached is not None:
        log.info("    (cached page)")
        return cached

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(5000)
        _click_spec_tab(page)
        html = page.content()
        browser.close()

    text = _strip_html(html)
    cache.set_page(url, rendered=True, text=text)
    return text


def url_variants(url: str) -> list[str]:
    parsed = urlparse(url)
    variants = [url]
    # + means space only in query strings, not paths.
    # DuckDuckGo puts + in paths where %20 belongs.
    if "+" in parsed.path:
        fixed = parsed._replace(path=parsed.path.replace("+", "%20"))
        variants.append(urlunparse(fixed))
    return variants


# ── Helpers ────────────────────────────────────────────────────

def _is_manufacturer_url(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return any(m in host.lower() for m in _MANUFACTURERS)


def _query_terms(query: str) -> list[str]:
    return [t.lower() for t in re.split(r"[\s\-]+", query) if len(t) >= 2]


def _relevance_score(query_terms: list[str], url: str, title: str) -> int:
    url_lower = url.lower()
    title_lower = title.lower()
    score = 0
    for term in query_terms:
        if term in url_lower:
            score += 2
        if term in title_lower:
            score += 1
    return score


def _strip_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def _click_spec_tab(page) -> bool:
    for label in _SPEC_TAB_PATTERNS:
        tab = page.locator(f"text='{label}'").first
        try:
            if tab.is_visible(timeout=500):
                tab.click()
                page.wait_for_timeout(2000)
                log.info("    Clicked tab: %s", label)
                return True
        except Exception:
            continue
    log.info("    No spec tab found")
    return False
