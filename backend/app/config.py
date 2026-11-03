from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NETWORKPATH_", env_file=".env", extra="ignore")

    database_url: str
    jwt_secret_key: SecretStr = Field(min_length=32)
    admin_username: str = Field(min_length=1, max_length=80)
    admin_password: SecretStr = Field(min_length=12)
    cors_origins: str = ""
    access_token_expire_minutes: int = Field(default=30, gt=0, le=1440)

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
