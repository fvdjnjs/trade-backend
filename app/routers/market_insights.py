from fastapi import APIRouter

from app.schemas.market_insights import KeywordInsightRequest, KeywordInsightResponse
from app.services.market_insights_service import generate_keyword_insights


router = APIRouter()


@router.post("/keywords", response_model=KeywordInsightResponse)
async def get_keyword_insights(payload: KeywordInsightRequest):
    return await generate_keyword_insights(payload)
