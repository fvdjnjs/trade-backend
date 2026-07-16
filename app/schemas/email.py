from pydantic import BaseModel, EmailStr, Field


class MailboxConnectRequest(BaseModel):
    email: EmailStr
    imap_host: str
    smtp_host: str


class ReplyDraftRequest(BaseModel):
    thread_id: str
    customer_message: str
    tone: str = "professional"
    customer_requirement: str | None = None
    reply_goal: str | None = None
    template_id: int | None = None
    user_id: int | None = None


class ReplyDraftResponse(BaseModel):
    thread_id: str
    draft_reply: str


class UnreadEmailRequest(BaseModel):
    user_id: int | None = Field(None, description="Optional user id. MVP uses demo user when empty.")
    imap_host: str = Field(..., description="IMAP 服务器地址，例如 imap.gmail.com")
    imap_port: int = Field(993, description="IMAP SSL 端口，常见值为 993")
    username: str = Field(..., description="邮箱账号")
    password: str = Field(..., repr=False, description="邮箱密码或应用专用密码")
    use_ssl: bool = Field(True, description="是否使用 SSL 连接")
    mailbox: str = Field("INBOX", description="要读取的邮箱目录")
    timeout_seconds: int = Field(20, ge=5, le=60, description="网络超时时间")
    max_emails: int = Field(10, ge=1, le=50, description="最多读取多少封未读邮件")


class EmailReplySuggestion(BaseModel):
    draft_id: int | None = None
    message_id: str
    sender: str
    subject: str
    received_at: str | None = None
    body: str
    ai_reply_draft: str


class UnreadEmailResponse(BaseModel):
    emails: list[EmailReplySuggestion]
