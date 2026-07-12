from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TimestampMixin:
    """统一记录创建和更新时间，便于后续做历史列表和审计。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(TimestampMixin, Base):
    """系统用户表。MVP 阶段可以先用默认用户，后续接入登录后再按真实用户写入。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="member", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    client_profiles: Mapped[list["ClientProfile"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    email_drafts: Mapped[list["EmailDraft"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    content_tasks: Mapped[list["ContentTask"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class ClientProfile(TimestampMixin, Base):
    """目标客户背调数据表，保存网页抓取和大模型提炼后的客户画像。"""

    __tablename__ = "client_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    website_url: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_text_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    main_business: Mapped[str | None] = mapped_column(Text, nullable=True)
    pain_points: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    target_customers: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="website_crawler", nullable=False)

    user: Mapped["User"] = relationship(back_populates="client_profiles")
    email_drafts: Mapped[list["EmailDraft"]] = relationship(
        back_populates="client_profile",
        cascade="all, delete-orphan",
    )


class EmailDraft(TimestampMixin, Base):
    """AI 生成的开发信和邮件回复草稿。只保存草稿，不代表已经发送。"""

    __tablename__ = "email_drafts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    client_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("client_profiles.id"),
        index=True,
        nullable=True,
    )
    draft_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    angle: Mapped[str | None] = mapped_column(String(120), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    source_email_message_id: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_email_sender: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_email_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_email_body_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="email_drafts")
    client_profile: Mapped["ClientProfile | None"] = relationship(back_populates="email_drafts")


class ContentTask(TimestampMixin, Base):
    """多语言本土化文案生成历史。"""

    __tablename__ = "content_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    chinese_selling_points: Mapped[str] = mapped_column(Text, nullable=False)
    target_market: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    target_language: Mapped[str] = mapped_column(String(80), nullable=False)
    copy_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    localized_copy: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)

    user: Mapped["User"] = relationship(back_populates="content_tasks")
