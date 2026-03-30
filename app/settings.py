"""
Application settings using Pydantic BaseSettings.
All environment variables are centralized here.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Use .env file for local development.
    """
    environment: str
    

    # Environment
    environment: str = "development"

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
    
    class Config:
        env_file = [".env", "../.env"]
        env_file_encoding = "utf-8"
        case_sensitive = False


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
