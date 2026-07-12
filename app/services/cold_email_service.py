import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.prompts import SYSTEM_PROMPTS
from app.services.persistence_service import (
    create_client_profile,
    create_email_draft,
    get_or_create_user,
)


# 这些关键词用于从客户官网首页中识别更有价值的子页面。
# 外贸开发信通常最需要 About、Products、Solutions、Services 等信息。
IMPORTANT_LINK_KEYWORDS = (
    "about",
    "company",
    "who-we-are",
    "profile",
    "product",
    "products",
    "solution",
    "solutions",
    "service",
    "services",
    "capability",
    "capabilities",
    "industry",
    "industries",
)


@dataclass
class CompanyInsights:
    main_business: str
    pain_points: list[str]
    target_customers: list[str]


def _normalize_url(url: str) -> str:
    """补齐 URL 协议，避免用户只输入 example.com 时请求失败。"""
    if url.startswith(("http://", "https://")):
        return url
    return f"https://{url}"


def _is_same_domain(source_url: str, target_url: str) -> bool:
    """只抓取同一个网站的页面，避免误抓外部社媒、广告或合作伙伴网站。"""
    source_host = urlparse(source_url).netloc.replace("www.", "")
    target_host = urlparse(target_url).netloc.replace("www.", "")
    return source_host == target_host


def _clean_text_lines(lines: list[str]) -> str:
    """去掉空行和重复行，让后续摘要输入更干净。"""
    cleaned: list[str] = []
    seen: set[str] = set()

    for line in lines:
        text = " ".join(line.split())
        if len(text) < 3 or text in seen:
            continue
        cleaned.append(text)
        seen.add(text)

    return "\n".join(cleaned)


def _extract_main_text(html: str) -> str:
    """从 HTML 中提取主要文本，移除脚本、样式、导航等噪音内容。"""
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript", "svg", "form", "nav", "footer"]):
        tag.decompose()

    lines: list[str] = []
    for selector in ["title", "h1", "h2", "h3", "p", "li"]:
        for node in soup.select(selector):
            text = node.get_text(" ", strip=True)
            if text:
                lines.append(text)

    return _clean_text_lines(lines)


def _extract_important_links(home_url: str, html: str, max_links: int = 4) -> list[str]:
    """从首页里找出 About、Products、Solutions 等更适合背调的子页面。"""
    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        link_text = anchor.get_text(" ", strip=True).lower()
        absolute_url = urljoin(home_url, href)
        match_text = f"{href} {link_text}".lower()

        if not _is_same_domain(home_url, absolute_url):
            continue

        if any(keyword in match_text for keyword in IMPORTANT_LINK_KEYWORDS):
            normalized = absolute_url.split("#")[0]
            if normalized not in links:
                links.append(normalized)

        if len(links) >= max_links:
            break

    return links


async def fetch_customer_website_text(customer_url: str, max_pages: int = 5) -> str:
    """
    抓取客户官网文本。

    当前 MVP 使用 BeautifulSoup 解析静态 HTML。多数 B2B 官网的 About、Products、
    Solutions 页面都能这样抓到。若后续遇到强依赖前端渲染的网站，再升级为 Playwright。
    """
    normalized_url = _normalize_url(customer_url)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0 Safari/537.36"
        )
    }

    async with httpx.AsyncClient(headers=headers, timeout=15, follow_redirects=True) as client:
        home_response = await client.get(normalized_url)
        home_response.raise_for_status()

        page_urls = [str(home_response.url)]
        page_urls.extend(_extract_important_links(str(home_response.url), home_response.text))
        page_urls = page_urls[:max_pages]

        page_texts: list[str] = []
        for page_url in page_urls:
            try:
                response = home_response if page_url == str(home_response.url) else await client.get(page_url)
                response.raise_for_status()
            except httpx.HTTPError:
                # 单个子页面抓取失败时跳过，不影响主流程。
                continue

            text = _extract_main_text(response.text)
            if text:
                page_texts.append(f"URL: {page_url}\n{text}")

    website_text = _clean_text_lines("\n".join(page_texts).splitlines())
    if not website_text:
        raise ValueError("未能从客户官网提取到有效文本，请检查 URL 是否可访问。")

    # 控制输入长度，避免一次性把过长网页内容送入大模型。
    return website_text[:18000]


def _load_json_from_llm_text(content: str) -> dict[str, Any]:
    """兼容模型偶尔在 JSON 前后添加说明文字的情况。"""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("大模型返回内容不是合法 JSON。")
        return json.loads(content[start : end + 1])


async def _call_openai_json(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> dict[str, Any]:
    """调用 OpenAI，并要求模型返回 JSON 对象。"""
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY 未配置，无法调用大模型生成内容。")

    # 延迟导入，避免未安装依赖时影响 FastAPI 启动和普通代码检查。
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.llm_model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = response.choices[0].message.content or "{}"
    return _load_json_from_llm_text(content)


async def summarize_company_profile(website_text: str) -> CompanyInsights:
    """让大模型从官网文本中提炼客户画像。"""
    system_prompt = (
        "You are a senior B2B sales researcher. "
        "Read company website text and return only valid JSON."
    )
    user_prompt = f"""
Please summarize the following company website text for cold email research.

Return JSON in this exact structure:
{{
  "main_business": "one concise paragraph",
  "pain_points": ["pain point 1", "pain point 2", "pain point 3"],
  "target_customers": ["customer group 1", "customer group 2", "customer group 3"]
}}

Website text:
{website_text}
"""

    data = await _call_openai_json(system_prompt, user_prompt)
    return CompanyInsights(
        main_business=str(data.get("main_business", "")).strip(),
        pain_points=[str(item).strip() for item in data.get("pain_points", []) if str(item).strip()],
        target_customers=[str(item).strip() for item in data.get("target_customers", []) if str(item).strip()],
    )


async def generate_cold_email_drafts(
    insights: CompanyInsights,
    product_value_props: str,
) -> list[dict[str, str]]:
    """基于客户画像和我方产品卖点，生成 3 个不同角度的英文开发信。"""
    system_prompt = SYSTEM_PROMPTS["cold_email"]
    user_prompt = f"""
Generate exactly 3 English cold email drafts.

Angles must be:
1. Direct pitch
2. Industry pain point discussion
3. Case study sharing

Company insights:
- Main business: {insights.main_business}
- Potential pain points: {", ".join(insights.pain_points)}
- Target customers: {", ".join(insights.target_customers)}

Our product value propositions:
{product_value_props}

Return JSON in this exact structure:
{{
  "emails": [
    {{
      "angle": "Direct pitch",
      "subject": "email subject",
      "body": "email body"
    }},
    {{
      "angle": "Industry pain point discussion",
      "subject": "email subject",
      "body": "email body"
    }},
    {{
      "angle": "Case study sharing",
      "subject": "email subject",
      "body": "email body"
    }}
  ]
}}

Writing requirements:
- Keep each email under 170 words.
- Avoid exaggerated claims.
- Mention the recipient company's business context.
- End with a low-pressure call to action.
"""

    data = await _call_openai_json(system_prompt, user_prompt, temperature=0.6)
    emails = data.get("emails", [])
    if not isinstance(emails, list) or len(emails) < 3:
        raise ValueError("大模型未返回 3 封开发信，请稍后重试。")

    drafts: list[dict[str, str]] = []
    for item in emails[:3]:
        if not isinstance(item, dict):
            continue
        drafts.append(
            {
                "angle": str(item.get("angle", "")).strip(),
                "subject": str(item.get("subject", "")).strip(),
                "body": str(item.get("body", "")).strip(),
            }
        )

    if len(drafts) != 3:
        raise ValueError("开发信结果格式不完整，请稍后重试。")

    return drafts


async def generate_cold_emails_from_website(
    customer_url: str,
    product_value_props: str,
    db: Session | None = None,
    user_id: int | None = None,
) -> list[dict[str, str | int | None]]:
    """完整流程：抓取官网、提炼客户画像、生成 3 封英文开发信。"""
    website_text = await fetch_customer_website_text(customer_url)
    insights = await summarize_company_profile(website_text)
    drafts = await generate_cold_email_drafts(insights, product_value_props)

    if db is None:
        return drafts

    user = get_or_create_user(db, user_id=user_id)
    client_profile = create_client_profile(
        db=db,
        user=user,
        website_url=customer_url,
        raw_text=website_text,
        main_business=insights.main_business,
        pain_points=insights.pain_points,
        target_customers=insights.target_customers,
    )

    saved_drafts: list[dict[str, str | int | None]] = []
    for draft in drafts:
        saved = create_email_draft(
            db=db,
            user=user,
            client_profile=client_profile,
            draft_type="cold_email",
            angle=draft["angle"],
            subject=draft["subject"],
            body=draft["body"],
        )
        saved_drafts.append(
            {
                "id": saved.id,
                "client_profile_id": client_profile.id,
                "angle": draft["angle"],
                "subject": draft["subject"],
                "body": draft["body"],
            }
        )

    db.commit()
    return saved_drafts
