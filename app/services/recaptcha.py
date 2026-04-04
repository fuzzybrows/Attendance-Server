import requests
import logging
from settings import settings

logger = logging.getLogger(__name__)

def verify_recaptcha(token: str) -> bool:
    """
    Verifies a Google reCAPTCHA v2 token against the Google API.
    Returns True if valid, False otherwise.
    """
    if not settings.recaptcha_enabled:
        return True
        
    if not settings.recaptcha_secret_key:
        logger.warning("RECAPTCHA_SECRET_KEY is not configured but recaptcha is enabled! Failing verification.")
        return False
        
    try:
        response = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": settings.recaptcha_secret_key,
                "response": token
            },
            timeout=5
        )
        data = response.json()
        if data.get("success"):
            return True
            
        logger.warning(f"reCAPTCHA validation failed: {data.get('error-codes')}")
        return False
        
    except Exception as e:
        logger.error(f"Error communicating with reCAPTCHA service: {e}")
        return False
