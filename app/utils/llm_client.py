from app.core.config import get_settings


async def generate_text(prompt: str) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        return f"LLM 未配置，当前提示词为：{prompt}"

    return "LLM 客户端待接入。"
