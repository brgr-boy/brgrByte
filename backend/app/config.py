from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BRGRBYTE_", env_file=".env", extra="ignore")

    database_url: str = Field(
        validation_alias=AliasChoices("BRGRBYTE_DATABASE_URL", "NETWORKPATH_DATABASE_URL")
    )
    jwt_secret_key: SecretStr = Field(
        min_length=32,
        validation_alias=AliasChoices("BRGRBYTE_JWT_SECRET_KEY", "NETWORKPATH_JWT_SECRET_KEY"),
    )
    admin_username: str = Field(
        min_length=1,
        max_length=80,
        validation_alias=AliasChoices("BRGRBYTE_ADMIN_USERNAME", "NETWORKPATH_ADMIN_USERNAME"),
    )
    admin_password: SecretStr = Field(
        min_length=12,
        validation_alias=AliasChoices("BRGRBYTE_ADMIN_PASSWORD", "NETWORKPATH_ADMIN_PASSWORD"),
    )
    cors_origins: str = Field(
        default="",
        validation_alias=AliasChoices("BRGRBYTE_CORS_ORIGINS", "NETWORKPATH_CORS_ORIGINS"),
    )
    access_token_expire_minutes: int = Field(
        default=30,
        gt=0,
        le=1440,
        validation_alias=AliasChoices(
            "BRGRBYTE_ACCESS_TOKEN_EXPIRE_MINUTES", "NETWORKPATH_ACCESS_TOKEN_EXPIRE_MINUTES"
        ),
    )

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
