from app.schemas.lead import LeadResearchRequest
from app.services.lead_research.crawler_service import crawl_company_website


async def build_company_profile(payload: LeadResearchRequest) -> str:
    website_text = await crawl_company_website(str(payload.website_url) if payload.website_url else None)

    if website_text:
        return f"{payload.company_name} 的官网信息已抓取，后续会接入 LLM 生成客户画像摘要。"

    return f"{payload.company_name} 的客户画像待补充，可先根据公司名称和目标市场生成初版分析。"
