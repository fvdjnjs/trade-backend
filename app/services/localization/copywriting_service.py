from app.schemas.localization import LocalizationRequest
from app.services.localization.market_style_service import get_market_style


async def localize_copy(payload: LocalizationRequest) -> str:
    market_style = get_market_style(payload.target_market)
    return (
        f"[{payload.target_language}] {payload.source_text}\n\n"
        f"本土化方向：{market_style}\n"
        f"语气：{payload.tone}"
    )
