"""
IP-based rate limiter for auth endpoints.
Uses an in-memory sliding-window counter per IP.
This replaces the spoofable X-Client-Platform header approach.
"""
import time
import threading
import logging
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)


class RateLimiter:
    """Thread-safe, in-memory sliding-window rate limiter."""

    def __init__(self):
        # { ip_string: [timestamp1, timestamp2, ...] }
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _cleanup(self, ip: str, window: int):
        """Remove timestamps outside the current window."""
        now = time.time()
        cutoff = now - window
        self._hits[ip] = [t for t in self._hits.get(ip, []) if t > cutoff]

    def check(self, ip: str, max_requests: int, window_seconds: int) -> bool:
        """
        Returns True if the request is allowed, False if rate-limited.
        """
        with self._lock:
            self._cleanup(ip, window_seconds)
            hits = self._hits.get(ip, [])
            if len(hits) >= max_requests:
                return False
            self._hits.setdefault(ip, []).append(time.time())
            return True

    def remaining(self, ip: str, max_requests: int, window_seconds: int) -> int:
        """Return how many requests remain in the current window."""
        with self._lock:
            self._cleanup(ip, window_seconds)
            return max(0, max_requests - len(self._hits.get(ip, [])))


# Singleton limiter instance
auth_limiter = RateLimiter()

# --- Configuration ---
# Login: 10 attempts per 5 minutes per IP
LOGIN_MAX = 10
LOGIN_WINDOW = 300  # seconds

# Forgot-password: 5 attempts per 15 minutes per IP
FORGOT_MAX = 5
FORGOT_WINDOW = 900


def get_client_ip(request: Request) -> str:
    """Extract the real client IP, respecting reverse-proxy headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_login_rate(request: Request):
    """Raises 429 if login rate limit is exceeded."""
    ip = get_client_ip(request)
    if not auth_limiter.check(ip, LOGIN_MAX, LOGIN_WINDOW):
        logger.warning("Login rate limit exceeded", extra={
            "type": "rate_limit_exceeded",
            "endpoint": "login",
            "ip": ip
        })
        raise HTTPException(
            status_code=429,
            detail=f"Too many login attempts. Please try again in a few minutes."
        )


def check_forgot_password_rate(request: Request):
    """Raises 429 if forgot-password rate limit is exceeded."""
    ip = get_client_ip(request)
    if not auth_limiter.check(ip, FORGOT_MAX, FORGOT_WINDOW):
        logger.warning("Forgot-password rate limit exceeded", extra={
            "type": "rate_limit_exceeded",
            "endpoint": "forgot_password",
            "ip": ip
        })
        raise HTTPException(
            status_code=429,
            detail="Too many reset attempts. Please try again later."
        )
