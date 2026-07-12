import asyncio
import html
import imaplib
import re
import socket
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email import message_from_bytes
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parseaddr, parsedate_to_datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.prompts import SYSTEM_PROMPTS
from app.services.persistence_service import create_email_draft, get_or_create_user


class EmailAssistantError(Exception):
    """邮件助理模块的基础异常，便于路由层统一转换成 HTTP 错误。"""


class EmailConnectionError(EmailAssistantError):
    """连接、登录、选择邮箱或网络超时时使用。"""


class EmailParseError(EmailAssistantError):
    """邮件内容无法解析时使用。"""


@dataclass
class ParsedEmail:
    message_id: str
    sender: str
    subject: str
    received_at: str | None
    body: str


def _decode_mime_header(value: str | None) -> str:
    """解码邮件标题或发件人中的 MIME 编码，兼容中文、日文等字符。"""
    if not value:
        return ""

    try:
        return str(make_header(decode_header(value))).strip()
    except Exception:
        return value.strip()


def _strip_html_tags(value: str) -> str:
    """当邮件只有 HTML 正文时，做一个轻量的标签清理，转成纯文本。"""
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    value = re.sub(r"(?is)<br\s*/?>", "\n", value)
    value = re.sub(r"(?is)</p\s*>", "\n", value)
    value = re.sub(r"(?is)<.*?>", " ", value)
    value = html.unescape(value)
    return _compact_text(value)


def _compact_text(value: str) -> str:
    """压缩多余空白，避免把很乱的邮件正文直接送给大模型。"""
    lines = [" ".join(line.split()) for line in value.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()


def _decode_payload(part: Message) -> str:
    """按邮件声明的字符集解码正文，声明缺失时用 utf-8 兜底。"""
    payload = part.get_payload(decode=True)
    if payload is None:
        raw_payload = part.get_payload()
        return raw_payload if isinstance(raw_payload, str) else ""

    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _extract_plain_body(message: Message) -> str:
    """优先提取 text/plain；如果没有纯文本，则把 text/html 简单转成纯文本。"""
    plain_parts: list[str] = []
    html_parts: list[str] = []

    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = (part.get("Content-Disposition") or "").lower()

            # 跳过附件，避免把 PDF、图片、报价单等二进制内容混入正文。
            if "attachment" in disposition:
                continue

            if content_type == "text/plain":
                plain_parts.append(_decode_payload(part))
            elif content_type == "text/html":
                html_parts.append(_decode_payload(part))
    else:
        content_type = message.get_content_type()
        if content_type == "text/plain":
            plain_parts.append(_decode_payload(message))
        elif content_type == "text/html":
            html_parts.append(_decode_payload(message))

    if plain_parts:
        return _compact_text("\n".join(plain_parts))

    if html_parts:
        return _strip_html_tags("\n".join(html_parts))

    return ""


def _parse_received_at(message: Message) -> datetime | None:
    """解析邮件 Date 头，并统一转成 UTC 时间。"""
    raw_date = message.get("Date")
    if not raw_date:
        return None

    try:
        parsed = parsedate_to_datetime(raw_date)
    except (TypeError, ValueError):
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def _parse_email_message(raw_message: bytes, fallback_message_id: str) -> ParsedEmail:
    """把 IMAP 返回的原始邮件字节解析成前端需要的结构。"""
    message = message_from_bytes(raw_message)
    sender_name, sender_email = parseaddr(_decode_mime_header(message.get("From")))
    subject = _decode_mime_header(message.get("Subject")) or "(No subject)"
    received_at = _parse_received_at(message)
    body = _extract_plain_body(message)

    if not body:
        raise EmailParseError("邮件正文为空或暂不支持该邮件格式。")

    sender = sender_email or sender_name or "unknown"
    message_id = (message.get("Message-ID") or fallback_message_id).strip()

    return ParsedEmail(
        message_id=message_id,
        sender=sender,
        subject=subject,
        received_at=received_at.isoformat() if received_at else None,
        body=body[:6000],
    )


def fetch_unread_customer_emails(
    imap_host: str,
    username: str,
    password: str,
    imap_port: int = 993,
    use_ssl: bool = True,
    mailbox_name: str = "INBOX",
    timeout_seconds: int = 20,
    max_emails: int = 10,
) -> list[ParsedEmail]:
    """
    通过 IMAP 读取最近 24 小时内的未读邮件。

    注意：
    - 使用 BODY.PEEK[] 读取邮件，避免把未读邮件标记为已读。
    - 这里只读取和解析邮件，不会发送邮件，也不会保存邮箱密码。
    """
    since_time = datetime.now(timezone.utc) - timedelta(hours=24)
    since_for_imap = since_time.strftime("%d-%b-%Y")
    mailbox: imaplib.IMAP4 | imaplib.IMAP4_SSL | None = None

    try:
        if use_ssl:
            mailbox = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=timeout_seconds)
        else:
            mailbox = imaplib.IMAP4(imap_host, imap_port, timeout=timeout_seconds)

        mailbox.login(username, password)
        status, _ = mailbox.select(mailbox_name, readonly=True)
        if status != "OK":
            raise EmailConnectionError(f"无法打开邮箱目录：{mailbox_name}")

        status, data = mailbox.search(None, f'(UNSEEN SINCE "{since_for_imap}")')
        if status != "OK":
            raise EmailConnectionError("IMAP 搜索未读邮件失败。")

        message_ids = data[0].split() if data and data[0] else []
        parsed_emails: list[ParsedEmail] = []

        # 默认从最新的未读邮件开始处理。
        for message_id in reversed(message_ids[-max_emails:]):
            status, fetched_data = mailbox.fetch(message_id, "(BODY.PEEK[])")
            if status != "OK" or not fetched_data:
                continue

            raw_message = None
            for item in fetched_data:
                if isinstance(item, tuple) and isinstance(item[1], bytes):
                    raw_message = item[1]
                    break

            if raw_message is None:
                continue

            try:
                parsed = _parse_email_message(raw_message, message_id.decode("utf-8", errors="ignore"))
            except EmailParseError:
                continue

            if parsed.received_at:
                received_at = datetime.fromisoformat(parsed.received_at)
                if received_at < since_time:
                    continue

            parsed_emails.append(parsed)

        return parsed_emails

    except (socket.timeout, TimeoutError) as exc:
        raise EmailConnectionError("连接邮箱服务器超时，请检查网络或 IMAP 配置。") from exc
    except imaplib.IMAP4.error as exc:
        raise EmailConnectionError(f"IMAP 登录或读取失败：{exc}") from exc
    except OSError as exc:
        raise EmailConnectionError(f"邮箱服务器连接失败：{exc}") from exc
    finally:
        if mailbox is not None:
            try:
                mailbox.close()
            except imaplib.IMAP4.error:
                pass
            try:
                mailbox.logout()
            except imaplib.IMAP4.error:
                pass


def _fallback_reply_draft(email_body: str) -> str:
    """没有配置大模型时使用的安全兜底草稿，明确这只是草稿，不会发送。"""
    short_context = _compact_text(email_body)[:400]
    return (
        "Draft reply only - please review before sending.\n\n"
        "Hi,\n\n"
        "Thank you for your message. I understand your concern and appreciate you sharing the details with us. "
        "We are reviewing the information and will get back to you with a clear answer as soon as possible.\n\n"
        f"Context noted: {short_context}\n\n"
        "Best regards,"
    )


async def generate_reply_draft_for_email(email_body: str) -> str:
    """
    调用大模型生成英文回复草稿。

    这个函数只返回草稿文本，不调用 SMTP，不发送邮件。
    如果未配置 OPENAI_API_KEY，则返回一份可人工编辑的兜底草稿。
    """
    settings = get_settings()
    if not settings.openai_api_key:
        return _fallback_reply_draft(email_body)

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.llm_model,
        temperature=0.4,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPTS["inquiry_reply"],
            },
            {
                "role": "user",
                "content": (
                    "Create a draft reply for the customer email below. "
                    "If the customer is upset, acknowledge the emotion and reassure them. "
                    "If the question is simple, answer clearly and ask for missing details if needed.\n\n"
                    f"Customer email:\n{email_body[:6000]}"
                ),
            },
        ],
    )

    draft = response.choices[0].message.content or ""
    draft = draft.strip()
    return f"Draft reply only - please review before sending.\n\n{draft}"


async def fetch_unread_emails_with_ai_suggestions(
    imap_host: str,
    username: str,
    password: str,
    imap_port: int = 993,
    use_ssl: bool = True,
    mailbox_name: str = "INBOX",
    timeout_seconds: int = 20,
    max_emails: int = 10,
    db: Session | None = None,
    user_id: int | None = None,
) -> list[dict[str, str | None]]:
    """读取未读邮件，并为每封邮件生成一份 AI 回复建议。"""
    emails = await asyncio.to_thread(
        fetch_unread_customer_emails,
        imap_host=imap_host,
        username=username,
        password=password,
        imap_port=imap_port,
        use_ssl=use_ssl,
        mailbox_name=mailbox_name,
        timeout_seconds=timeout_seconds,
        max_emails=max_emails,
    )

    results: list[dict[str, str | None]] = []
    user = get_or_create_user(db, user_id=user_id) if db is not None else None

    for item in emails:
        try:
            draft = await generate_reply_draft_for_email(item.body)
        except Exception:
            # 大模型失败时不影响邮件读取，返回兜底草稿供人工编辑。
            draft = _fallback_reply_draft(item.body)

        saved_draft_id: int | None = None
        if db is not None and user is not None:
            saved = create_email_draft(
                db=db,
                user=user,
                draft_type="email_reply",
                body=draft,
                subject=f"Re: {item.subject}",
                source_email_message_id=item.message_id,
                source_email_sender=item.sender,
                source_email_subject=item.subject,
                source_email_body=item.body,
            )
            saved_draft_id = saved.id

        results.append(
            {
                "draft_id": saved_draft_id,
                "message_id": item.message_id,
                "sender": item.sender,
                "subject": item.subject,
                "received_at": item.received_at,
                "body": item.body,
                "ai_reply_draft": draft,
            }
        )

    if db is not None:
        db.commit()

    return results
