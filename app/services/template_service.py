from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import EmailTemplate
from app.schemas.template import EmailTemplateCreate, EmailTemplateUpdate


DEFAULT_EMAIL_TEMPLATES = [
    {
        "name": "首封开发信：价值切入",
        "category": "cold_email",
        "scenario": "第一次联系目标客户，重点说明你能帮他解决什么问题",
        "subject_template": "A practical idea for {company_name}",
        "body_template": (
            "Hi {contact_name},\n\n"
            "I noticed {company_name} works in {customer_business}.\n\n"
            "Many teams in this space run into {customer_pain_point}. "
            "We help suppliers improve {product_value} without adding extra work for the sales team.\n\n"
            "Would it be worth sharing a short example based on your market?"
        ),
        "tone": "direct",
        "variables": ["company_name", "contact_name", "customer_business", "customer_pain_point", "product_value"],
    },
    {
        "name": "未回复跟进：轻压力提醒",
        "category": "cold_email",
        "scenario": "首封开发信 3-5 天后未回复，提醒但不催促",
        "subject_template": "Re: {topic}",
        "body_template": (
            "Hi {contact_name},\n\n"
            "Just wanted to follow up on my note below.\n\n"
            "If {topic} is not a focus right now, no problem. "
            "If it is something your team is reviewing, I can send a few practical points that may help you compare options.\n\n"
            "Best,\n{sender_name}"
        ),
        "tone": "low_pressure",
        "variables": ["contact_name", "topic", "sender_name"],
    },
    {
        "name": "询价回复：确认需求",
        "category": "inquiry_reply",
        "scenario": "客户询问价格，但规格、数量或目的地还不完整",
        "subject_template": "Re: Price for {product_name}",
        "body_template": (
            "Hi {contact_name},\n\n"
            "Thanks for your inquiry. We can prepare a clear quotation for {product_name}.\n\n"
            "To quote accurately, could you please confirm the quantity, key specifications, and destination port/country? "
            "Once we have these details, we will send the price and lead time for your review.\n\n"
            "Best regards,\n{sender_name}"
        ),
        "tone": "professional",
        "variables": ["contact_name", "product_name", "sender_name"],
    },
    {
        "name": "样品申请：推进下一步",
        "category": "inquiry_reply",
        "scenario": "客户想要样品，需要确认规格、收货信息和样品费用规则",
        "subject_template": "Re: Sample request for {product_name}",
        "body_template": (
            "Hi {contact_name},\n\n"
            "Yes, we can arrange samples for {product_name}.\n\n"
            "Please send the required specification, quantity, receiver address, and courier account if available. "
            "We will confirm the sample cost and estimated preparation time before arranging anything.\n\n"
            "Best regards,\n{sender_name}"
        ),
        "tone": "helpful",
        "variables": ["contact_name", "product_name", "sender_name"],
    },
    {
        "name": "投诉安抚：先稳住情绪",
        "category": "inquiry_reply",
        "scenario": "客户反馈质量、包装、数量或服务问题，需要先承接情绪并收集证据",
        "subject_template": "Re: Your concern about {order_or_product}",
        "body_template": (
            "Hi {contact_name},\n\n"
            "I understand your concern, and we will check this carefully.\n\n"
            "Could you please send photos or videos showing the issue, along with the order number and quantity affected? "
            "Our team will review the details and come back with a clear solution as soon as possible.\n\n"
            "Best regards,\n{sender_name}"
        ),
        "tone": "calm",
        "variables": ["contact_name", "order_or_product", "sender_name"],
    },
    {
        "name": "交期延误说明：负责但不乱承诺",
        "category": "inquiry_reply",
        "scenario": "订单生产或物流延误，需要解释当前状态并给客户可执行更新",
        "subject_template": "Update on {order_or_product}",
        "body_template": (
            "Hi {contact_name},\n\n"
            "I want to give you a direct update on {order_or_product}.\n\n"
            "The current status is {current_status}. We are checking the fastest workable option and will keep you updated with the next confirmed step. "
            "I will send another update by {update_time}.\n\n"
            "Best regards,\n{sender_name}"
        ),
        "tone": "responsible",
        "variables": ["contact_name", "order_or_product", "current_status", "update_time", "sender_name"],
    },
]


def seed_default_templates(db: Session) -> None:
    existing_count = db.scalar(select(EmailTemplate).where(EmailTemplate.is_system.is_(True)).limit(1))
    if existing_count:
        return

    for item in DEFAULT_EMAIL_TEMPLATES:
        db.add(EmailTemplate(**item, is_system=True, user_id=None))
    db.commit()


def list_templates(db: Session, category: str | None = None, user_id: int | None = None) -> list[EmailTemplate]:
    seed_default_templates(db)

    stmt = select(EmailTemplate).where(or_(EmailTemplate.is_system.is_(True), EmailTemplate.user_id == user_id))
    if category:
        stmt = stmt.where(EmailTemplate.category == category)
    stmt = stmt.order_by(EmailTemplate.category, EmailTemplate.id)
    return list(db.scalars(stmt).all())


def get_template(db: Session, template_id: int, user_id: int | None = None) -> EmailTemplate | None:
    seed_default_templates(db)
    stmt = select(EmailTemplate).where(
        EmailTemplate.id == template_id,
        or_(EmailTemplate.is_system.is_(True), EmailTemplate.user_id == user_id),
    )
    return db.scalar(stmt)


def create_template(db: Session, payload: EmailTemplateCreate) -> EmailTemplate:
    template = EmailTemplate(**payload.model_dump(), is_system=False)
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def update_template(db: Session, template: EmailTemplate, payload: EmailTemplateUpdate) -> EmailTemplate:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, key, value)
    db.commit()
    db.refresh(template)
    return template
