import requests
from bs4 import BeautifulSoup
from ddgs import DDGS


def search(query: str, result_index: int = 0) -> str:
    with DDGS() as ddgs:
        results = list(ddgs.text(f"{query} motherboard specifications", max_results=5))
    if not results:
        raise ValueError(f"No results found for: {query}")
    if result_index >= len(results):
        raise ValueError(f"Only {len(results)} results found, asked for #{result_index + 1}")
    for i, r in enumerate(results):
        marker = " <--" if i == result_index else ""
        print(f"  [{i + 1}] {r['href']}{marker}")
    return results[result_index]["href"]


def fetch_text(url: str) -> str:
    response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    return soup.get_text(separator="\n", strip=True)
