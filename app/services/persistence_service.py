from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ClientProfile, ContentTask, EmailDraft, User


DEFAULT_USER_EMAIL = "demo@example.com"
DEFAULT_USER_NAME = "Demo User"


def get_or_create_user(db: Session, user_id: int | None = None) -> User:
    """MVP 阶段的用户获取逻辑。没有登录系统时，使用默认用户承接数据。"""
    if user_id is not None:
        user = db.get(User, user_id)
        if user:
            return user

    user = db.scalar(select(User).where(User.email == DEFAULT_USER_EMAIL))
    if user:
        return user

    user = User(email=DEFAULT_USER_EMAIL, name=DEFAULT_USER_NAME)
    db.add(user)
    db.flush()
    return user


def guess_company_name_from_url(url: str) -> str:
    """从官网域名里推断一个公司名，后续可由大模型或用户手动修正。"""
    host = urlparse(url).netloc or urlparse(f"https://{url}").netloc
    host = host.replace("www.", "")
    if not host:
        return "Unknown Company"

    main_part = host.split(".")[0]
    return main_part.replace("-", " ").replace("_", " ").title()


def create_client_profile(
    db: Session,
    user: User,
    website_url: str,
    raw_text: str,
    main_business: str,
    pain_points: list[str],
    target_customers: list[str],
    company_name: str | None = None,
) -> ClientProfile:
    profile = ClientProfile(
        user_id=user.id,
        company_name=company_name or guess_company_name_from_url(website_url),
        website_url=website_url,
        raw_text_excerpt=raw_text[:5000],
        main_business=main_business,
        pain_points=pain_points,
        target_customers=target_customers,
    )
    db.add(profile)
    db.flush()
    return profile


def create_email_draft(
    db: Session,
    user: User,
    body: str,
    draft_type: str,
    client_profile: ClientProfile | None = None,
    angle: str | None = None,
    subject: str | None = None,
    source_email_message_id: str | None = None,
    source_email_sender: str | None = None,
    source_email_subject: str | None = None,
    source_email_body: str | None = None,
) -> EmailDraft:
    draft = EmailDraft(
        user_id=user.id,
        client_profile_id=client_profile.id if client_profile else None,
        draft_type=draft_type,
        angle=angle,
        subject=subject,
        body=body,
        source_email_message_id=source_email_message_id,
        source_email_sender=source_email_sender,
        source_email_subject=source_email_subject,
        source_email_body_excerpt=source_email_body[:3000] if source_email_body else None,
    )
    db.add(draft)
    db.flush()
    return draft


def create_content_task(
    db: Session,
    user: User,
    chinese_selling_points: str,
    target_market: str,
    target_language: str,
    copy_type: str,
    localized_copy: str,
    notes: list[str],
) -> ContentTask:
    task = ContentTask(
        user_id=user.id,
        chinese_selling_points=chinese_selling_points,
        target_market=target_market,
        target_language=target_language,
        copy_type=copy_type,
        localized_copy=localized_copy,
        notes=notes,
    )
    db.add(task)
    db.flush()
    return task
