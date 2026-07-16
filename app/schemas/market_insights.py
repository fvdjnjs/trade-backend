from pydantic import BaseModel, Field, HttpUrl


class KeywordInsightRequest(BaseModel):
    seed_keywords: list[str] = Field(..., min_length=1, max_length=10, description="种子关键词")
    target_market: str = Field("美国", description="目标国家/市场")
    page_url: HttpUrl | None = Field(None, description="可选商品页或官网 URL")
    language_id: str | None = Field(None, description="Google Ads language constant id")
    location_ids: list[str] | None = Field(None, description="Google Ads geo target constant ids")
    limit: int = Field(20, ge=5, le=50)


class MonthlySearchVolume(BaseModel):
    year: int
    month: str
    monthly_searches: int


class KeywordInsightItem(BaseModel):
    keyword: str
    avg_monthly_searches: int
    competition: str
    competition_index: int | None = None
    low_top_of_page_bid_micros: int | None = None
    high_top_of_page_bid_micros: int | None = None
    monthly_search_volumes: list[MonthlySearchVolume] = Field(default_factory=list)


class KeywordInsightSummary(BaseModel):
    total_keywords: int
    highest_volume_keyword: str | None = None
    average_monthly_searches: int
    high_competition_count: int


class KeywordInsightResponse(BaseModel):
    source: str
    target_market: str
    target_language: str
    google_ads_configured: bool
    items: list[KeywordInsightItem]
    summary: KeywordInsightSummary
    notes: list[str] = Field(default_factory=list)
