import requests
from bs4 import BeautifulSoup
from ddgs import DDGS


def search(query: str) -> str:
    with DDGS() as ddgs:
        results = list(ddgs.text(f"{query} motherboard specifications", max_results=3))
    if not results:
        raise ValueError(f"No results found for: {query}")
    return results[0]["href"]


def fetch_text(url: str) -> str:
    response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    return soup.get_text(separator="\n", strip=True)
