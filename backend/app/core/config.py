from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경변수 기반 설정. 비밀정보는 코드에 두지 않는다."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TodoMate AI"
    environment: str = "local"
    timezone: str = "Asia/Seoul"
    log_level: str = "INFO"

    database_url: str = ""
    redis_url: str = ""
    openai_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
