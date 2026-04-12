"""
Application settings using Pydantic BaseSettings.
All environment variables are centralized here.
"""
from enum import Enum
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List


class Environment(str, Enum):
    LOCAL = "local"
    DEV = "dev"
    CI = "ci"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Use .env file for local development.
    """
    # Environment
    environment: Environment = Environment.LOCAL

    # JWT / Auth
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    
    # Twilio
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_verify_service_sid: str
    twilio_phone_number: str
    
    # SendGrid
    sendgrid_api_key: str = "placeholder_sendgrid_key"
    
    # Firebase Cloud Messaging
    firebase_credentials_path: str = "placeholder_firebase_path"
    
    # Database
    database_url: str
    
    # CORS
    cors_origins: str = ""  # Comma-separated additional origins, e.g. "https://example.com,http://example.com"
    
    # Google OAuth
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: Optional[str] = None
    # Comma-separated list of trusted redirect origins for OAuth callbacks.
    # Supports web origins (https://app.com) and mobile schemes (attendanceapp://).
    allowed_redirect_origins: str = "http://localhost:5173"

    @property
    def allowed_redirect_origins_list(self) -> list:
        """Parsed list of trusted redirect origins."""
        return [o.strip() for o in self.allowed_redirect_origins.split(",") if o.strip()]

    @property
    def default_redirect_url(self) -> str:
        """First HTTP(S) origin in the allowlist, used as a fallback redirect destination."""
        first_web = next(
            (o for o in self.allowed_redirect_origins_list if o.startswith("http")),
            "http://localhost:5173"
        )
        return f"{first_web}/calendar"

    def is_redirect_allowed(self, app_redirect: str) -> bool:
        """Security check: ensure the redirect target starts with a trusted origin."""
        return any(app_redirect.startswith(origin) for origin in self.allowed_redirect_origins_list)
    
    # Recaptcha
    recaptcha_secret_key: Optional[str] = None
    recaptcha_enabled: bool = True
    
    model_config = SettingsConfigDict(
        env_file=[".env", "../.env"],
        env_file_encoding="utf-8",
        case_sensitive=False
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Use dependency injection in FastAPI routes:
        settings: Settings = Depends(get_settings)
    """
    return Settings()


# Convenience instance for direct imports
settings = get_settings()
