from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chat import ChatAskRequest, ChatAskResponse, ChatMessageOut, ChatSessionCreate, ChatSessionOut
from app.services.ai_chat_service import (
    ask_chat,
    create_chat_session,
    get_chat_session,
    list_chat_messages,
    list_chat_sessions,
)


router = APIRouter()


@router.get("/sessions", response_model=list[ChatSessionOut])
def get_sessions(user_id: int | None = Query(None), db: Session = Depends(get_db)):
    return list_chat_sessions(db, user_id=user_id)


@router.post("/sessions", response_model=ChatSessionOut)
def add_session(payload: ChatSessionCreate, db: Session = Depends(get_db)):
    return create_chat_session(db, title=payload.title, scenario=payload.scenario, user_id=payload.user_id)


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
def get_messages(session_id: int, user_id: int | None = Query(None), db: Session = Depends(get_db)):
    session = get_chat_session(db, session_id=session_id, user_id=user_id)
    if not session:
        raise HTTPException(status_code=404, detail="对话不存在")
    return list_chat_messages(db, session)


@router.post("/sessions/{session_id}/ask", response_model=ChatAskResponse)
async def ask(session_id: int, payload: ChatAskRequest, db: Session = Depends(get_db)):
    session = get_chat_session(db, session_id=session_id, user_id=payload.user_id)
    if not session:
        raise HTTPException(status_code=404, detail="对话不存在")

    user_message, assistant_message = await ask_chat(db, session=session, message=payload.message)
    return ChatAskResponse(session=session, user_message=user_message, assistant_message=assistant_message)
