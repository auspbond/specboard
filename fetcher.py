from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS


def url_variants(url: str) -> list[str]:
    parsed = urlparse(url)
    variants = [url]
    # + means space only in query strings, not paths.
    # DuckDuckGo puts + in paths where %20 belongs.
    if "+" in parsed.path:
        fixed = parsed._replace(path=parsed.path.replace("+", "%20"))
        variants.append(urlunparse(fixed))
    return variants


def search(query: str) -> list[str]:
    with DDGS() as ddgs:
        results = list(ddgs.text(f"{query} motherboard specifications", max_results=5))
    if not results:
        raise ValueError(f"No results found for: {query}")
    urls = [r["href"] for r in results]
    for i, url in enumerate(urls):
        print(f"  [{i + 1}] {url}")
    return urls


def _strip_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def fetch_text(url: str) -> str:
    response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    return _strip_html(response.text)


_SPEC_TAB_PATTERNS = [
    "Specification",
    "Specifications",
    "Specs",
    "Tech Specs",
    "Technical Specifications",
    "Features & Specifications",
]


def _click_spec_tab(page) -> bool:
    for label in _SPEC_TAB_PATTERNS:
        tab = page.locator(f"a:text-is('{label}'), button:text-is('{label}')").first
        if tab.is_visible():
            tab.click()
            page.wait_for_timeout(2000)
            print(f"  Clicked tab: {label}")
            return True
    return False


def fetch_rendered(url: str) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(5000)
        _click_spec_tab(page)
        html = page.content()
        browser.close()

    return _strip_html(html)
