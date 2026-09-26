from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NCPC_", env_file=".env", extra="ignore")

    database_url: str = "sqlite+pysqlite:///./ncpc-dev.db"
    environment: str = "development"
    admin_bootstrap_token: str | None = Field(default=None, min_length=24)
    admin_bootstrap_client_id: str = "bootstrap-admin"
    cors_origins: list[str] = Field(default_factory=list)
    log_level: str = "INFO"
    max_request_bytes: int = Field(default=1_048_576, ge=16_384, le=10_485_760)
    rate_limit_per_minute: int = Field(default=120, ge=10, le=10_000)


@lru_cache
def get_settings() -> Settings:
    return Settings()
