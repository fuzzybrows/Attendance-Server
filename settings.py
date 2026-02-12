"""
Application settings using Pydantic BaseSettings.
All environment variables are centralized here.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Use .env file for local development.
    """
    
    # JWT / Auth
    secret_key: str = "your-secret-key-for-choir-attendance-server"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 1 week
    
    # Twilio
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_verify_service_sid: str
    twilio_phone_number: str
    
    # SendGrid
    sendgrid_api_key: str = "placeholder_sendgrid_key"
    
    # Database
    database_url: str = "sqlite:///./attendance.db"
    
    class Config:
        env_file = ".env"
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
