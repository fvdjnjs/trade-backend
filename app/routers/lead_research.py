from fastapi import APIRouter

from app.schemas.lead import LeadResearchRequest, LeadResearchResponse
from app.services.lead_research.company_profile_service import build_company_profile
from app.services.lead_research.outreach_email_service import generate_outreach_email


router = APIRouter()


@router.post("/research", response_model=LeadResearchResponse)
async def research_lead(payload: LeadResearchRequest):
    profile_summary = await build_company_profile(payload)
    outreach_email = await generate_outreach_email(payload, profile_summary)

    return LeadResearchResponse(
        company_name=payload.company_name,
        profile_summary=profile_summary,
        outreach_email=outreach_email,
    )
