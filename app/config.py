from typing import Literal
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "Retail Intelligence Platform"
    APP_ENV: Literal["development", "testing", "production"] = "development"
    DATABASE_URL: str = "postgresql+asyncpg://retail_user:retail_secure_password_2026@localhost:5432/retail_intelligence"
    LOG_LEVEL: Literal["debug", "info", "warning", "error", "critical"] = "info"
    API_V1_STR: str = "/api/v1"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL cannot be empty")
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v


settings = Settings()
