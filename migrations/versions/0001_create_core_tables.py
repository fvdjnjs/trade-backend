"""create core tables

Revision ID: 0001_create_core_tables
Revises: None
Create Date: 2026-07-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_create_core_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "client_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("website_url", sa.String(length=500), nullable=False),
        sa.Column("raw_text_excerpt", sa.Text(), nullable=True),
        sa.Column("main_business", sa.Text(), nullable=True),
        sa.Column("pain_points", sa.JSON(), nullable=False),
        sa.Column("target_customers", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_client_profiles_company_name"), "client_profiles", ["company_name"], unique=False)
    op.create_index(op.f("ix_client_profiles_id"), "client_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_client_profiles_user_id"), "client_profiles", ["user_id"], unique=False)

    op.create_table(
        "content_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("chinese_selling_points", sa.Text(), nullable=False),
        sa.Column("target_market", sa.String(length=120), nullable=False),
        sa.Column("target_language", sa.String(length=80), nullable=False),
        sa.Column("copy_type", sa.String(length=80), nullable=False),
        sa.Column("localized_copy", sa.Text(), nullable=False),
        sa.Column("notes", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_content_tasks_copy_type"), "content_tasks", ["copy_type"], unique=False)
    op.create_index(op.f("ix_content_tasks_id"), "content_tasks", ["id"], unique=False)
    op.create_index(op.f("ix_content_tasks_target_market"), "content_tasks", ["target_market"], unique=False)
    op.create_index(op.f("ix_content_tasks_user_id"), "content_tasks", ["user_id"], unique=False)

    op.create_table(
        "email_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("client_profile_id", sa.Integer(), nullable=True),
        sa.Column("draft_type", sa.String(length=50), nullable=False),
        sa.Column("angle", sa.String(length=120), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("source_email_message_id", sa.String(length=500), nullable=True),
        sa.Column("source_email_sender", sa.String(length=255), nullable=True),
        sa.Column("source_email_subject", sa.String(length=500), nullable=True),
        sa.Column("source_email_body_excerpt", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["client_profile_id"], ["client_profiles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_email_drafts_client_profile_id"), "email_drafts", ["client_profile_id"], unique=False)
    op.create_index(op.f("ix_email_drafts_draft_type"), "email_drafts", ["draft_type"], unique=False)
    op.create_index(op.f("ix_email_drafts_id"), "email_drafts", ["id"], unique=False)
    op.create_index(op.f("ix_email_drafts_user_id"), "email_drafts", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_email_drafts_user_id"), table_name="email_drafts")
    op.drop_index(op.f("ix_email_drafts_id"), table_name="email_drafts")
    op.drop_index(op.f("ix_email_drafts_draft_type"), table_name="email_drafts")
    op.drop_index(op.f("ix_email_drafts_client_profile_id"), table_name="email_drafts")
    op.drop_table("email_drafts")

    op.drop_index(op.f("ix_content_tasks_user_id"), table_name="content_tasks")
    op.drop_index(op.f("ix_content_tasks_target_market"), table_name="content_tasks")
    op.drop_index(op.f("ix_content_tasks_id"), table_name="content_tasks")
    op.drop_index(op.f("ix_content_tasks_copy_type"), table_name="content_tasks")
    op.drop_table("content_tasks")

    op.drop_index(op.f("ix_client_profiles_user_id"), table_name="client_profiles")
    op.drop_index(op.f("ix_client_profiles_id"), table_name="client_profiles")
    op.drop_index(op.f("ix_client_profiles_company_name"), table_name="client_profiles")
    op.drop_table("client_profiles")

    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
