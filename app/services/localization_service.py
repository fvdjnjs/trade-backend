import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.prompts import SYSTEM_PROMPTS
from app.services.persistence_service import create_content_task, get_or_create_user


MARKET_GUIDES: dict[str, dict[str, str]] = {
    "美国": {
        "language": "English",
        "style": "Emphasize practicality, convenience, clear benefits, time savings, and everyday use cases.",
    },
    "德国": {
        "language": "German",
        "style": "Emphasize precision, durability, material quality, safety, standards, and reliable specifications.",
    },
    "日本": {
        "language": "Japanese",
        "style": "Emphasize thoughtful design, reliability, compactness, politeness, detail, and long-term trust.",
    },
    "英国": {
        "language": "English",
        "style": "Use restrained, credible language. Emphasize quality, reliability, and practical value without hype.",
    },
    "法国": {
        "language": "French",
        "style": "Emphasize design, aesthetics, comfort, craftsmanship, and refined lifestyle value.",
    },
    "意大利": {
        "language": "Italian",
        "style": "Emphasize design, texture, craftsmanship, elegance, and product experience.",
    },
    "西班牙": {
        "language": "Spanish",
        "style": "Emphasize value, ease of use, family or daily-life scenarios, and clear product benefits.",
    },
    "加拿大": {
        "language": "English",
        "style": "Emphasize practical value, safety, durability, and suitability for diverse usage scenarios.",
    },
    "澳大利亚": {
        "language": "English",
        "style": "Emphasize durability, outdoor or daily practicality, ease of use, and straightforward benefits.",
    },
    "中东": {
        "language": "English",
        "style": "Emphasize premium quality, reliability, business credibility, service support, and long-term cooperation.",
    },
}


COPY_TYPE_GUIDES: dict[str, str] = {
    "标题": "Create 5 marketplace-ready product titles. Keep them concise, keyword-rich, and natural.",
    "五点描述": "Create 5 bullet points. Each bullet should focus on one clear buyer benefit.",
    "详情页详情": "Create a structured product detail page section with a headline, short paragraphs, and feature blocks.",
}


def _get_market_guide(target_market: str) -> dict[str, str]:
    """根据目标市场返回语言和表达偏好，未知市场使用英文通用外贸风格。"""
    return MARKET_GUIDES.get(
        target_market,
        {
            "language": "English",
            "style": "Use natural, buyer-focused international B2B/B2C copy with clear benefits and credible wording.",
        },
    )


def _get_copy_type_guide(copy_type: str) -> str:
    """根据文案类型返回格式要求，未知类型按通用营销文案处理。"""
    return COPY_TYPE_GUIDES.get(
        copy_type,
        "Create localized product copy with a clear headline, benefit-focused paragraphs, and concise selling points.",
    )


def _parse_json_object(content: str) -> dict[str, Any]:
    """解析模型返回的 JSON；兼容模型在 JSON 前后多写说明的情况。"""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("大模型返回内容不是合法 JSON。")
        return json.loads(content[start : end + 1])


def _build_system_prompt() -> str:
    return SYSTEM_PROMPTS["localized_product_copy"]


def _build_fallback_copy(
    chinese_selling_points: str,
    target_market: str,
    copy_type: str,
) -> dict[str, Any]:
    """没有配置大模型时返回开发期可用的兜底结果，避免接口直接不可用。"""
    market_guide = _get_market_guide(target_market)
    return {
        "target_language": market_guide["language"],
        "localized_copy": (
            f"[Draft localized copy for {target_market} / {market_guide['language']}]\n\n"
            f"Copy type: {copy_type}\n\n"
            f"Source selling points:\n{chinese_selling_points}\n\n"
            f"Localization direction: {market_guide['style']}"
        ),
        "notes": [
            "OPENAI_API_KEY 未配置，当前返回的是开发期兜底草稿。",
            "正式使用时会调用大模型完成真正的本土化转译。",
        ],
    }


async def generate_localized_product_copy(
    chinese_selling_points: str,
    target_market: str,
    copy_type: str,
    db: Session | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    """
    调用大模型生成本土化产品文案。

    参数：
    - chinese_selling_points：中文产品卖点
    - target_market：目标国家或市场
    - copy_type：标题、五点描述、详情页详情等
    """
    settings = get_settings()
    market_guide = _get_market_guide(target_market)
    copy_type_guide = _get_copy_type_guide(copy_type)

    if not settings.openai_api_key:
        result = _build_fallback_copy(chinese_selling_points, target_market, copy_type)
        if db is not None:
            user = get_or_create_user(db, user_id=user_id)
            task = create_content_task(
                db=db,
                user=user,
                chinese_selling_points=chinese_selling_points,
                target_market=target_market,
                target_language=result["target_language"],
                copy_type=copy_type,
                localized_copy=result["localized_copy"],
                notes=result["notes"],
            )
            db.commit()
            result["task_id"] = task.id
        return result

    from openai import AsyncOpenAI

    user_prompt = f"""
Target market: {target_market}
Target language: {market_guide["language"]}
Market style guide: {market_guide["style"]}

Copy type: {copy_type}
Copy format guide: {copy_type_guide}

Chinese product selling points:
{chinese_selling_points}

Please generate localized product copy now.
"""

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.llm_model,
        temperature=0.55,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = response.choices[0].message.content or "{}"
    result = _parse_json_object(content)

    result = {
        "target_language": str(result.get("target_language") or market_guide["language"]),
        "localized_copy": str(result.get("localized_copy") or "").strip(),
        "notes": [str(item).strip() for item in result.get("notes", []) if str(item).strip()],
    }

    if db is not None:
        user = get_or_create_user(db, user_id=user_id)
        task = create_content_task(
            db=db,
            user=user,
            chinese_selling_points=chinese_selling_points,
            target_market=target_market,
            target_language=result["target_language"],
            copy_type=copy_type,
            localized_copy=result["localized_copy"],
            notes=result["notes"],
        )
        db.commit()
        result["task_id"] = task.id

    return result
