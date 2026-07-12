from pydantic import BaseModel, Field


class LocalizationRequest(BaseModel):
    source_text: str
    target_language: str
    target_market: str | None = None
    tone: str = "natural"


class LocalizationResponse(BaseModel):
    target_language: str
    target_market: str | None = None
    localized_text: str


class ProductLocalizationRequest(BaseModel):
    user_id: int | None = Field(None, description="Optional user id. MVP uses demo user when empty.")
    chinese_selling_points: str = Field(..., min_length=5, description="中文产品卖点")
    target_market: str = Field(..., description="目标国家或市场，例如：美国、德国、日本")
    copy_type: str = Field(..., description="文案类型，例如：标题、五点描述、详情页详情")


class ProductLocalizationResponse(BaseModel):
    task_id: int | None = None
    target_market: str
    target_language: str
    copy_type: str
    localized_copy: str
    notes: list[str] = Field(default_factory=list, description="本土化处理说明")
