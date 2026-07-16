from datetime import datetime

from pydantic import BaseModel, Field


class EmailTemplateBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    category: str = Field(..., description="cold_email 或 inquiry_reply")
    scenario: str = Field(..., description="模板适用场景")
    subject_template: str = Field(..., min_length=2, max_length=500)
    body_template: str = Field(..., min_length=10)
    tone: str = "professional"
    variables: list[str] = Field(default_factory=list)


class EmailTemplateCreate(EmailTemplateBase):
    user_id: int | None = None


class EmailTemplateUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    scenario: str | None = None
    subject_template: str | None = None
    body_template: str | None = None
    tone: str | None = None
    variables: list[str] | None = None


class EmailTemplateOut(EmailTemplateBase):
    id: int
    user_id: int | None = None
    is_system: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
