from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.localization import (
    LocalizationRequest,
    LocalizationResponse,
    ProductLocalizationRequest,
    ProductLocalizationResponse,
)
from app.services.localization_service import generate_localized_product_copy
from app.services.localization.copywriting_service import localize_copy


router = APIRouter()


@router.post("/generate", response_model=LocalizationResponse)
async def generate_localized_copy(payload: LocalizationRequest):
    localized_text = await localize_copy(payload)
    return LocalizationResponse(
        target_language=payload.target_language,
        target_market=payload.target_market,
        localized_text=localized_text,
    )


@router.post("/product-copy", response_model=ProductLocalizationResponse)
async def generate_product_localization(
    payload: ProductLocalizationRequest,
    db: Session = Depends(get_db),
):
    result = await generate_localized_product_copy(
        chinese_selling_points=payload.chinese_selling_points,
        target_market=payload.target_market,
        copy_type=payload.copy_type,
        db=db,
        user_id=payload.user_id,
    )

    return ProductLocalizationResponse(
        task_id=result.get("task_id"),
        target_market=payload.target_market,
        target_language=result["target_language"],
        copy_type=payload.copy_type,
        localized_copy=result["localized_copy"],
        notes=result["notes"],
    )
