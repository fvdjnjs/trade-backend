from pydantic import BaseModel, Field, HttpUrl


class ColdEmailGenerateRequest(BaseModel):
    customer_url: HttpUrl = Field(..., description="客户官网 URL")
    product_value_props: str = Field(..., min_length=10, description="我方产品卖点")
    customer_requirement: str | None = Field(None, description="客户当前需求、采购意向或沟通背景")
    email_purpose: str | None = Field(None, description="本次邮件目的，如首次开发、跟进、报价前确认")
    target_contact: str | None = Field(None, description="目标联系人或岗位，如 Purchasing Manager")
    template_id: int | None = Field(None, description="邮件模板 ID")
    user_id: int | None = Field(None, description="可选用户 ID，MVP 为空时使用演示用户")


class CompanyInsight(BaseModel):
    main_business: str = Field(..., description="客户公司的主营业务")
    pain_points: list[str] = Field(..., description="客户可能存在的业务痛点")
    target_customers: list[str] = Field(..., description="客户公司的目标客户群")


class ColdEmailDraft(BaseModel):
    id: int | None = Field(None, description="保存后的草稿 ID")
    client_profile_id: int | None = Field(None, description="保存后的客户画像 ID")
    angle: str = Field(..., description="开发信角度")
    subject: str = Field(..., description="英文邮件标题")
    body: str = Field(..., description="英文邮件正文")
