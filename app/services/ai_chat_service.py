from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import ChatMessage, ChatSession
from app.services.persistence_service import get_or_create_user


CHAT_SYSTEM_PROMPT = """
<prompt>
  <role>
    You are an experienced B2B export sales coach inside a foreign trade SaaS workbench.
    You help users analyze customer requirements, choose email templates, polish replies, and plan next sales actions.
  </role>
  <working_style>
    <rule>Ask for missing business information only when it affects the answer.</rule>
    <rule>Give practical sales wording the user can send or adapt.</rule>
    <rule>When writing emails, sound human, concise, and commercially mature.</rule>
    <rule>Never claim an email has been sent. Everything is a draft until the user sends it manually.</rule>
    <rule>Remember the customer's stated needs, objections, target market, product, price concerns, and next steps from the conversation.</rule>
  </working_style>
  <banned_language>
    <word>Furthermore</word>
    <word>Moreover</word>
    <word>Delve</word>
    <word>Crucial</word>
    <word>Leverage</word>
    <word>Seamless</word>
    <word>Robust</word>
    <phrase>I hope this email finds you well</phrase>
  </banned_language>
</prompt>
"""


def create_chat_session(db: Session, title: str, scenario: str, user_id: int | None = None) -> ChatSession:
    user = get_or_create_user(db, user_id=user_id)
    session = ChatSession(user_id=user.id, title=title, scenario=scenario)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_chat_sessions(db: Session, user_id: int | None = None) -> list[ChatSession]:
    user = get_or_create_user(db, user_id=user_id)
    stmt = select(ChatSession).where(ChatSession.user_id == user.id).order_by(ChatSession.updated_at.desc())
    return list(db.scalars(stmt).all())


def get_chat_session(db: Session, session_id: int, user_id: int | None = None) -> ChatSession | None:
    user = get_or_create_user(db, user_id=user_id)
    return db.scalar(select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user.id))


def list_chat_messages(db: Session, session: ChatSession) -> list[ChatMessage]:
    stmt = select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc())
    return list(db.scalars(stmt).all())


async def _call_chat_llm(session: ChatSession, history: list[ChatMessage], message: str) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        return (
            "这是一个演示回复：我会先确认客户的核心诉求，再建议使用合适模板。\n\n"
            "如果客户在询价，建议先问清规格、数量和目的港；如果客户在抱怨，先承接情绪并收集证据；"
            "如果是冷启动开发，第一封邮件只突出一个明确价值点，不带附件。"
        )

    from openai import AsyncOpenAI

    recent_history = history[-12:]
    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                f"Conversation scenario: {session.scenario}\n"
                f"Memory summary: {session.memory_summary or 'No saved memory yet.'}"
            ),
        },
    ]
    messages.extend({"role": item.role, "content": item.content} for item in recent_history)
    messages.append({"role": "user", "content": message})

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.llm_model,
        temperature=0.45,
        messages=messages,
    )
    return response.choices[0].message.content or ""


def _refresh_memory_summary(session: ChatSession, messages: list[ChatMessage]) -> None:
    important_lines: list[str] = []
    for item in messages[-10:]:
        if item.role == "user":
            important_lines.append(item.content.strip())

    joined = "\n".join(line for line in important_lines if line)
    session.memory_summary = joined[:2000] if joined else session.memory_summary


async def ask_chat(db: Session, session: ChatSession, message: str) -> tuple[ChatMessage, ChatMessage]:
    history = list_chat_messages(db, session)
    assistant_text = await _call_chat_llm(session, history, message)

    user_message = ChatMessage(session_id=session.id, role="user", content=message)
    assistant_message = ChatMessage(session_id=session.id, role="assistant", content=assistant_text)
    db.add_all([user_message, assistant_message])
    db.flush()

    _refresh_memory_summary(session, [*history, user_message])
    db.commit()
    db.refresh(session)
    db.refresh(user_message)
    db.refresh(assistant_message)
    return user_message, assistant_message
