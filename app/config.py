from pydantic_settings import BaseSettings
from pydantic import field_validator, ValidationInfo


class Settings(BaseSettings):
    """Application settings loaded from environment (or .env).

    Required in production: `SESSION_SECRET_KEY`, Keycloak client credentials.
    """
    # App Config
    ENV: str = "dev"
    SESSION_SECRET_KEY: str | None = None

    # Keycloak Config
    KEYCLOAK_CLIENT_ID: str | None = None
    KEYCLOAK_CLIENT_SECRET: str | None = None
    KEYCLOAK_REALM: str | None = None
    KEYCLOAK_SERVER_URL: str = "http://localhost:8080"
    # Optional: allow overriding metadata/jwks url explicitly
    KEYCLOAK_METADATA_URL: str | None = None
    # Optional admin client for Keycloak Admin REST API (used for user sync)
    KEYCLOAK_ADMIN_CLIENT_ID: str | None = None
    KEYCLOAK_ADMIN_CLIENT_SECRET: str | None = None
    
    # Cache TTL Settings (in seconds)
    JWKS_CACHE_TTL: int = 600  # 10 minutes - JWKS keys rarely change
    JWKS_CACHE_MAXSIZE: int = 2  # Small cache, only need current JWKS
    ADMIN_TOKEN_CACHE_TTL: int = 300  # 5 minutes - admin tokens expire quickly
    ADMIN_TOKEN_CACHE_MAXSIZE: int = 1  # Only one admin token needed
    USER_INFO_CACHE_TTL: int = 300  # 5 minutes - user info can change
    USER_INFO_CACHE_MAXSIZE: int = 100  # Cache up to 100 users
    GROUP_CACHE_TTL: int = 600  # 10 minutes - group structure changes infrequently
    GROUP_CACHE_MAXSIZE: int = 50  # Cache up to 50 groups

    @property
    def metadata_url(self) -> str:
        if self.KEYCLOAK_METADATA_URL:
            return self.KEYCLOAK_METADATA_URL
        if not (self.KEYCLOAK_SERVER_URL and self.KEYCLOAK_REALM):
            return ""
        return f"{self.KEYCLOAK_SERVER_URL}/realms/{self.KEYCLOAK_REALM}/.well-known/openid-configuration"

    @field_validator("SESSION_SECRET_KEY", mode='before')
    def ensure_session_secret(cls, v, info: ValidationInfo):
        env = info.data.get("ENV", "dev")
        if env == "prod" and not v:
            raise ValueError("SESSION_SECRET_KEY must be set in production")
        # In dev, generate a default weak secret if not provided (not for prod)
        return v or "dev-secret-change-me"

    class Config:
        env_file = ".env"


# Instantiate settings to be imported elsewhere
settings = Settings()