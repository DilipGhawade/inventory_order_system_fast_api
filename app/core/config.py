from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application Metadata
    PROJECT_NAME: str = "Enterprise Inventory & Order Management API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production", "testing"] = "development"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # Security & Cryptography
    SECRET_KEY: str = Field(
        default="f9bf78b9a18ce6d46a0cd2b0b86df9da8f3451c29b3e1a7c45e87a90d1e2b3c4",
        min_length=32,
    )
    REFRESH_SECRET_KEY: str = Field(
        default="a1b2c3d4e5f60718293a4b5c6d7e8f901a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
        min_length=32,
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=1440)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=90)
    BCRYPT_ROUNDS: int = Field(default=12, ge=4, le=16)

    # PostgreSQL Connection & Pool Settings
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "inventory_user"
    POSTGRES_PASSWORD: str = "inventory_secure_password"
    POSTGRES_DB: str = "inventory_db"
    DATABASE_URL: str = (
        "postgresql+asyncpg://inventory_user:inventory_secure_password@localhost:5432/inventory_db"
    )
    TEST_DATABASE_URL: str = "sqlite+aiosqlite:///./test_inventory.db"

    DB_POOL_SIZE: int = Field(default=20, ge=1, le=100)
    DB_MAX_OVERFLOW: int = Field(default=10, ge=0, le=50)
    DB_POOL_TIMEOUT: int = Field(default=30, ge=5, le=120)
    DB_POOL_RECYCLE: int = Field(default=1800, ge=60)
    DB_ECHO: bool = False

    # Middleware & Network
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1", "*"]

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_JSON_FORMAT: bool = True

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        if isinstance(v, list):
            return v
        raise ValueError(f"Invalid CORS_ORIGINS format: {v}")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()