from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.email import (
    MailboxConnectRequest,
    ReplyDraftRequest,
    ReplyDraftResponse,
    UnreadEmailRequest,
    UnreadEmailResponse,
)
from app.services.email_assistant_service import (
    EmailConnectionError,
    fetch_unread_emails_with_ai_suggestions,
)
from app.services.mail_assistant.reply_draft_service import generate_reply_draft
from app.services.persistence_service import create_email_draft, get_or_create_user


router = APIRouter()


@router.post("/connect")
async def connect_mailbox(payload: MailboxConnectRequest):
    return {
        "status": "pending",
        "message": "邮箱连接参数已接收，后续步骤会接入 IMAP/SMTP 登录验证。",
        "email": payload.email,
    }


@router.post("/draft-reply", response_model=ReplyDraftResponse)
async def draft_reply(payload: ReplyDraftRequest, db: Session = Depends(get_db)):
    draft = await generate_reply_draft(payload, db=db)
    user = get_or_create_user(db, user_id=payload.user_id)
    create_email_draft(
        db=db,
        user=user,
        draft_type="email_reply",
        body=draft,
        subject=f"Reply draft for thread {payload.thread_id}",
        source_email_message_id=payload.thread_id,
        source_email_body=payload.customer_message,
    )
    db.commit()
    return ReplyDraftResponse(thread_id=payload.thread_id, draft_reply=draft)


@router.post("/unread-suggestions", response_model=UnreadEmailResponse)
async def get_unread_email_suggestions(payload: UnreadEmailRequest, db: Session = Depends(get_db)):
    """
    读取最近 24 小时未读邮件，并返回 AI 回复草稿。

    重要说明：这里不会发送邮件，只会生成可人工确认和修改的草稿文本。
    """
    try:
        emails = await fetch_unread_emails_with_ai_suggestions(
            imap_host=payload.imap_host,
            imap_port=payload.imap_port,
            username=payload.username,
            password=payload.password,
            use_ssl=payload.use_ssl,
            mailbox_name=payload.mailbox,
            timeout_seconds=payload.timeout_seconds,
            max_emails=payload.max_emails,
            db=db,
            user_id=payload.user_id,
        )
        return UnreadEmailResponse(emails=emails)
    except EmailConnectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="读取邮件或生成回复建议失败，请稍后重试。") from exc
