from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "外贸全流程提效工作台"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./app/db/trade_workbench.sqlite3"
    openai_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    google_ads_developer_token: str | None = None
    google_ads_client_id: str | None = None
    google_ads_client_secret: str | None = None
    google_ads_refresh_token: str | None = None
    google_ads_login_customer_id: str | None = None
    google_ads_customer_id: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_allowed_origins() -> list[str]:
    settings = get_settings()
    return [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
