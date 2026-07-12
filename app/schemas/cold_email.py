from pydantic import BaseModel, Field, HttpUrl


class ColdEmailGenerateRequest(BaseModel):
    customer_url: HttpUrl = Field(..., description="Customer website URL")
    product_value_props: str = Field(..., min_length=10, description="Our product value propositions")
    user_id: int | None = Field(None, description="Optional user id. MVP uses demo user when empty.")


class CompanyInsight(BaseModel):
    main_business: str = Field(..., description="客户公司的主营业务")
    pain_points: list[str] = Field(..., description="客户可能存在的业务痛点")
    target_customers: list[str] = Field(..., description="客户公司的目标客户群")


class ColdEmailDraft(BaseModel):
    id: int | None = Field(None, description="Database id of the saved draft")
    client_profile_id: int | None = Field(None, description="Database id of the saved client profile")
    angle: str = Field(..., description="开发信角度")
    subject: str = Field(..., description="英文邮件标题")
    body: str = Field(..., description="英文邮件正文")
