from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.cold_email import ColdEmailDraft, ColdEmailGenerateRequest
from app.services.cold_email_service import generate_cold_emails_from_website


router = APIRouter()


@router.post("/cold-emails", response_model=list[ColdEmailDraft])
async def generate_cold_emails(payload: ColdEmailGenerateRequest, db: Session = Depends(get_db)):
    """
    接收客户官网 URL 和我方产品卖点，返回 3 封英文开发信。

    返回值是 JSON 数组，每一项包含：
    - angle：开发信角度
    - subject：邮件标题
    - body：邮件正文
    """
    try:
        return await generate_cold_emails_from_website(
            customer_url=str(payload.customer_url),
            product_value_props=payload.product_value_props,
            customer_requirement=payload.customer_requirement,
            email_purpose=payload.email_purpose,
            target_contact=payload.target_contact,
            template_id=payload.template_id,
            db=db,
            user_id=payload.user_id,
        )
    except ValueError as exc:
        # 输入 URL 无法抓取、网页无有效文本、模型返回格式异常等，归为请求处理失败。
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        # 常见情况是未配置 OPENAI_API_KEY。
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        # 兜底保护，避免把内部异常堆栈直接暴露给前端。
        raise HTTPException(status_code=502, detail="开发信生成失败，请稍后重试。") from exc
