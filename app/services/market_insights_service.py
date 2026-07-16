import asyncio
from typing import Any

from app.core.config import get_settings
from app.schemas.market_insights import (
    KeywordInsightItem,
    KeywordInsightRequest,
    KeywordInsightResponse,
    KeywordInsightSummary,
    MonthlySearchVolume,
)


MARKET_TARGETS: dict[str, dict[str, str]] = {
    "美国": {"language_id": "1000", "language": "English", "location_id": "2840"},
    "德国": {"language_id": "1001", "language": "German", "location_id": "2276"},
    "日本": {"language_id": "1005", "language": "Japanese", "location_id": "2392"},
    "英国": {"language_id": "1000", "language": "English", "location_id": "2826"},
    "法国": {"language_id": "1002", "language": "French", "location_id": "2250"},
    "意大利": {"language_id": "1004", "language": "Italian", "location_id": "2380"},
    "西班牙": {"language_id": "1003", "language": "Spanish", "location_id": "2724"},
    "加拿大": {"language_id": "1000", "language": "English", "location_id": "2124"},
    "澳大利亚": {"language_id": "1000", "language": "English", "location_id": "2036"},
    "中东": {"language_id": "1000", "language": "English", "location_id": "2784"},
}


def _google_ads_configured() -> bool:
    settings = get_settings()
    required_values = [
        settings.google_ads_developer_token,
        settings.google_ads_client_id,
        settings.google_ads_client_secret,
        settings.google_ads_refresh_token,
        settings.google_ads_customer_id,
    ]
    return all(bool(value) for value in required_values)


def _clean_customer_id(value: str | None) -> str | None:
    return value.replace("-", "").strip() if value else None


def _market_config(target_market: str) -> dict[str, str]:
    return MARKET_TARGETS.get(
        target_market,
        {"language_id": "1000", "language": "English", "location_id": "2840"},
    )


def _build_summary(items: list[KeywordInsightItem]) -> KeywordInsightSummary:
    if not items:
        return KeywordInsightSummary(total_keywords=0, average_monthly_searches=0, high_competition_count=0)

    highest = max(items, key=lambda item: item.avg_monthly_searches)
    total_searches = sum(item.avg_monthly_searches for item in items)
    return KeywordInsightSummary(
        total_keywords=len(items),
        highest_volume_keyword=highest.keyword,
        average_monthly_searches=round(total_searches / len(items)),
        high_competition_count=sum(1 for item in items if item.competition.upper() == "HIGH"),
    )


def _demo_keyword_ideas(payload: KeywordInsightRequest) -> list[KeywordInsightItem]:
    base_keywords = payload.seed_keywords[:]
    suggestions: list[str] = []
    for keyword in base_keywords:
        suggestions.extend(
            [
                keyword,
                f"{keyword} for travel",
                f"portable {keyword}",
                f"best {keyword}",
                f"{keyword} set",
                f"{keyword} supplier",
            ]
        )

    deduped: list[str] = []
    for keyword in suggestions:
        normalized = keyword.strip()
        if normalized and normalized.lower() not in {item.lower() for item in deduped}:
            deduped.append(normalized)

    demo_months = [
        ("JANUARY", 8200),
        ("FEBRUARY", 9100),
        ("MARCH", 10300),
        ("APRIL", 11800),
        ("MAY", 14600),
        ("JUNE", 17200),
    ]
    competitions = ["LOW", "MEDIUM", "HIGH"]

    items: list[KeywordInsightItem] = []
    for index, keyword in enumerate(deduped[: payload.limit]):
        monthly_base = max(1000, 18000 - index * 1350)
        items.append(
            KeywordInsightItem(
                keyword=keyword,
                avg_monthly_searches=monthly_base,
                competition=competitions[index % len(competitions)],
                competition_index=min(100, 28 + index * 7),
                low_top_of_page_bid_micros=350000 + index * 45000,
                high_top_of_page_bid_micros=1300000 + index * 90000,
                monthly_search_volumes=[
                    MonthlySearchVolume(year=2026, month=month, monthly_searches=max(100, value - index * 600))
                    for month, value in demo_months
                ],
            )
        )
    return items


def _build_google_ads_client():
    settings = get_settings()
    from google.ads.googleads.client import GoogleAdsClient

    config: dict[str, Any] = {
        "developer_token": settings.google_ads_developer_token,
        "client_id": settings.google_ads_client_id,
        "client_secret": settings.google_ads_client_secret,
        "refresh_token": settings.google_ads_refresh_token,
        "use_proto_plus": True,
    }
    login_customer_id = _clean_customer_id(settings.google_ads_login_customer_id)
    if login_customer_id:
        config["login_customer_id"] = login_customer_id

    return GoogleAdsClient.load_from_dict(config)


def _fetch_google_keyword_ideas(payload: KeywordInsightRequest) -> list[KeywordInsightItem]:
    settings = get_settings()
    market = _market_config(payload.target_market)
    client = _build_google_ads_client()

    keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")
    google_ads_service = client.get_service("GoogleAdsService")
    request = client.get_type("GenerateKeywordIdeasRequest")
    request.customer_id = _clean_customer_id(settings.google_ads_customer_id)
    request.language = google_ads_service.language_constant_path(payload.language_id or market["language_id"])

    location_ids = payload.location_ids or [market["location_id"]]
    for location_id in location_ids:
        request.geo_target_constants.append(google_ads_service.geo_target_constant_path(location_id))

    request.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH_AND_PARTNERS
    keywords = [keyword.strip() for keyword in payload.seed_keywords if keyword.strip()]

    if payload.page_url and keywords:
        request.keyword_and_url_seed.url = str(payload.page_url)
        request.keyword_and_url_seed.keywords.extend(keywords)
    elif payload.page_url:
        request.url_seed.url = str(payload.page_url)
    else:
        request.keyword_seed.keywords.extend(keywords)

    response = keyword_plan_idea_service.generate_keyword_ideas(request=request)
    items: list[KeywordInsightItem] = []
    for idea in response:
        metrics = idea.keyword_idea_metrics
        monthly_volumes = [
            MonthlySearchVolume(
                year=int(volume.year),
                month=volume.month.name,
                monthly_searches=int(volume.monthly_searches),
            )
            for volume in metrics.monthly_search_volumes
        ]
        items.append(
            KeywordInsightItem(
                keyword=str(idea.text),
                avg_monthly_searches=int(metrics.avg_monthly_searches or 0),
                competition=metrics.competition.name,
                competition_index=getattr(metrics, "competition_index", None),
                low_top_of_page_bid_micros=getattr(metrics, "low_top_of_page_bid_micros", None),
                high_top_of_page_bid_micros=getattr(metrics, "high_top_of_page_bid_micros", None),
                monthly_search_volumes=monthly_volumes,
            )
        )
        if len(items) >= payload.limit:
            break

    return sorted(items, key=lambda item: item.avg_monthly_searches, reverse=True)


async def generate_keyword_insights(payload: KeywordInsightRequest) -> KeywordInsightResponse:
    market = _market_config(payload.target_market)
    configured = _google_ads_configured()

    if not configured:
        items = _demo_keyword_ideas(payload)
        return KeywordInsightResponse(
            source="demo",
            target_market=payload.target_market,
            target_language=market["language"],
            google_ads_configured=False,
            items=items,
            summary=_build_summary(items),
            notes=[
                "Google Ads API 凭证未配置完整，当前显示的是演示热词数据。",
                "配置 GOOGLE_ADS_DEVELOPER_TOKEN、GOOGLE_ADS_CLIENT_ID、GOOGLE_ADS_CLIENT_SECRET、GOOGLE_ADS_REFRESH_TOKEN、GOOGLE_ADS_CUSTOMER_ID 后会读取真实关键词数据。",
            ],
        )

    try:
        items = await asyncio.to_thread(_fetch_google_keyword_ideas, payload)
        return KeywordInsightResponse(
            source="google_ads",
            target_market=payload.target_market,
            target_language=market["language"],
            google_ads_configured=True,
            items=items,
            summary=_build_summary(items),
            notes=["数据来自 Google Ads Keyword Planner，适合判断搜索需求、竞争度和文案关键词方向。"],
        )
    except Exception as exc:
        items = _demo_keyword_ideas(payload)
        return KeywordInsightResponse(
            source="demo_after_error",
            target_market=payload.target_market,
            target_language=market["language"],
            google_ads_configured=True,
            items=items,
            summary=_build_summary(items),
            notes=[
                "Google Ads API 调用失败，当前先返回演示数据，避免页面不可用。",
                f"后端错误摘要：{type(exc).__name__}",
            ],
        )
