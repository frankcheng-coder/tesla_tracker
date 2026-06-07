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
    # TODO(you): generate a stable key and put it in .env, otherwise stored
    # Tesla tokens cannot be decrypted after a restart. Generate with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    token_encryption_key: str = ""

    # Tesla Fleet API OAuth
    # TODO(you): all four come from the Tesla Developer portal
    #   (https://developer.tesla.com -> your app). Put them in backend/.env.
    #   See README "Connect your own Tesla" for the full setup checklist.
    tesla_client_id: str = ""        # TODO: Client ID from the Tesla Developer app
    tesla_client_secret: str = ""    # TODO: Client Secret from the Tesla Developer app
    tesla_redirect_uri: str = ""     # TODO: must EXACTLY match an Allowed Redirect URI in the portal
    tesla_developer_domain: str = "" # TODO: the public HTTPS domain hosting your com.tesla.3p.public-key.pem
    # TODO(you): pick the audience for YOUR account's region. North America/Asia-Pacific:
    #   https://fleet-api.prd.na.vn.cloud.tesla.com
    # Europe/Middle East/Africa:
    #   https://fleet-api.prd.eu.vn.cloud.tesla.com
    tesla_audience: str = "https://fleet-api.prd.na.vn.cloud.tesla.com"

    # Path to the EC key pair. This server hosts the PUBLIC key at
    #   /.well-known/appspecific/com.tesla.3p.public-key.pem
    # Generate the pair with:  python -m app.tesla_setup genkey
    tesla_public_key_path: str = "keys/com.tesla.3p.public-key.pem"
    tesla_private_key_path: str = "keys/com.tesla.3p.private-key.pem"

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
