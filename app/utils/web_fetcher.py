import httpx
from bs4 import BeautifulSoup

from app.utils.text_cleaner import compact_text


async def fetch_page_text(url: str) -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    return compact_text(soup.get_text(" "))[:5000]
