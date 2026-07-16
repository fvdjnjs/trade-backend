from datetime import datetime

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    title: str = Field("新的 AI 销售对话", max_length=200)
    scenario: str = Field("general", description="general, cold_email, inquiry_reply, localization")
    user_id: int | None = None


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionOut(BaseModel):
    id: int
    title: str
    scenario: str
    memory_summary: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatAskRequest(BaseModel):
    message: str = Field(..., min_length=1)
    user_id: int | None = None


class ChatAskResponse(BaseModel):
    session: ChatSessionOut
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut
