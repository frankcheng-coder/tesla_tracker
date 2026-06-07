"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings.

    Values are read from the process environment and an optional `.env` file.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    database_url: str = "postgresql+psycopg2://tesla:tesla@localhost:5432/tesla_tracker"

    # Encryption
    token_encryption_key: str = ""

    # Tesla Fleet API OAuth
    tesla_client_id: str = ""
    tesla_client_secret: str = ""
    tesla_redirect_uri: str = ""
    tesla_developer_domain: str = ""
    tesla_audience: str = "https://fleet-api.prd.na.vn.cloud.tesla.com"

    # App behaviour
    cors_origins: str = "*"
    use_mock_data: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # Tesla OAuth endpoints (derived from audience region in a real deployment;
    # kept here as constants for the placeholder implementation).
    @property
    def tesla_authorize_url(self) -> str:
        return "https://auth.tesla.com/oauth2/v3/authorize"

    @property
    def tesla_token_url(self) -> str:
        return "https://auth.tesla.com/oauth2/v3/token"

    # Read-only scopes only. Command scopes are intentionally omitted.
    @property
    def tesla_scopes(self) -> list[str]:
        return ["openid", "offline_access", "vehicle_device_data", "vehicle_location"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
