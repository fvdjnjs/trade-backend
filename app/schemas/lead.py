from pydantic import BaseModel, HttpUrl


class LeadResearchRequest(BaseModel):
    company_name: str
    website_url: HttpUrl | None = None
    target_market: str | None = None
    product_name: str | None = None


class LeadResearchResponse(BaseModel):
    company_name: str
    profile_summary: str
    outreach_email: str
