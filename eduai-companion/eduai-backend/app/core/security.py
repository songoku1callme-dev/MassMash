"""Security middleware: rate limiting, CORS, and security headers."""

import time
import logging
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate Limiting (in-memory, per-IP)
# ---------------------------------------------------------------------------

# Stores: ip -> list of request timestamps
_rate_limit_store: dict[str, list[float]] = defaultdict(list)

# Config
RATE_LIMIT_MAX_REQUESTS = 5   # max requests per window
RATE_LIMIT_WINDOW_SEC = 60    # window size in seconds
RATE_LIMIT_PATHS = ("/api/auth/login", "/api/auth/register", "/api/auth/refresh")


def _client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For behind proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


def _is_rate_limited(ip: str) -> bool:
    """Return True if the IP has exceeded the rate limit."""
    now = time.monotonic()
    # Prune old entries
    window_start = now - RATE_LIMIT_WINDOW_SEC
    _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if t > window_start]
    if len(_rate_limit_store[ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return True
    _rate_limit_store[ip].append(now)
    return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate-limit auth endpoints: max 5 requests per minute per IP."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        path = request.url.path
        if any(path.startswith(p) for p in RATE_LIMIT_PATHS):
            ip = _client_ip(request)
            if _is_rate_limited(ip):
                logger.warning("Rate limit exceeded for IP %s on %s", ip, path)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please try again later."},
                )
        return await call_next(request)


# ---------------------------------------------------------------------------
# Security Headers
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        response: Response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'"
        )
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response


# ---------------------------------------------------------------------------
# CORS allowed origins
# ---------------------------------------------------------------------------

# Allowed frontend origins — extend as needed
ALLOWED_ORIGINS = [
    "https://eduai-german-tutor-app-mzmkkhlp.devinapps.com",
    "https://mass-mash-git-devin-1772317-607977-songoku1callme-devs-projects.vercel.app",
    "https://massmash.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
]
