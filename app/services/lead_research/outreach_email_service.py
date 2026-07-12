from app.schemas.lead import LeadResearchRequest


async def generate_outreach_email(payload: LeadResearchRequest, profile_summary: str) -> str:
    product_line = f"我们注意到贵司可能关注 {payload.product_name}。" if payload.product_name else ""
    market_line = f"针对 {payload.target_market} 市场，" if payload.target_market else ""

    return (
        f"您好，我们正在了解 {payload.company_name} 的业务方向。"
        f"{product_line}{market_line}"
        f"希望基于以下背景与您探讨合作机会：{profile_summary}"
    )
