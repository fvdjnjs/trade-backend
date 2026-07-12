from app.utils.web_fetcher import fetch_page_text


async def crawl_company_website(website_url: str | None) -> str:
    if not website_url:
        return ""
    return await fetch_page_text(website_url)
