def get_market_style(target_market: str | None) -> str:
    if not target_market:
        return "保持自然、清晰、适合跨境电商和 B2B 外贸场景。"

    return f"面向 {target_market} 市场，使用当地买家更容易接受的表达方式。"
