from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.template import EmailTemplateCreate, EmailTemplateOut, EmailTemplateUpdate
from app.services.template_service import create_template, get_template, list_templates, update_template


router = APIRouter()


@router.get("", response_model=list[EmailTemplateOut])
def get_templates(
    category: str | None = Query(None, description="cold_email 或 inquiry_reply"),
    user_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    return list_templates(db, category=category, user_id=user_id)


@router.post("", response_model=EmailTemplateOut)
def add_template(payload: EmailTemplateCreate, db: Session = Depends(get_db)):
    return create_template(db, payload)


@router.put("/{template_id}", response_model=EmailTemplateOut)
def edit_template(
    template_id: int,
    payload: EmailTemplateUpdate,
    user_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    template = get_template(db, template_id=template_id, user_id=user_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    if template.is_system:
        raise HTTPException(status_code=400, detail="系统内置模板不能直接修改，请新建自定义模板")
    return update_template(db, template, payload)
