from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.config import get_allowed_origins
from app.routers import chat, cold_email, lead_research, localization, mail_assistant, templates


app = FastAPI(
    title="外贸全流程提效工作台 API",
    description="面向外贸团队的客户背调、邮件助理和多语言文案生成平台",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "trade-ai-workbench"}


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "trade-ai-workbench"}


@app.get("/health/env")
def health_env():
    settings = get_settings()
    return {
        "status": "ok",
        "openai_api_key_configured": bool(settings.openai_api_key),
        "database_url_configured": bool(settings.database_url),
        "llm_model": settings.llm_model,
    }


app.include_router(
    lead_research.router,
    prefix="/api/lead-research",
    tags=["客户背调与开发信生成"],
)

app.include_router(
    cold_email.router,
    prefix="/api/lead-research",
    tags=["客户背调与开发信生成"],
)

app.include_router(
    mail_assistant.router,
    prefix="/api/mail-assistant",
    tags=["7x24 邮件助理"],
)

app.include_router(
    localization.router,
    prefix="/api/localization",
    tags=["多语言本土化文案引擎"],
)

app.include_router(
    templates.router,
    prefix="/api/templates",
    tags=["邮件模板库"],
)

app.include_router(
    chat.router,
    prefix="/api/chat",
    tags=["AI 对话工作台"],
)
