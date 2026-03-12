"""Security middleware: rate limiting, CORS, security headers, and bot protection.

Iron Shield Security Package:
- Shield 3: Enhanced rate limiting (tier-based for chat, strict for auth)
- Shield 6: Security headers (CSP, X-Frame-Options, HSTS, Permissions-Policy)
- Shield 10: Bot protection (user-agent validation, request body size limit)
"""

import os
import time
import logging
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shield 3: Enhanced Rate Limiting (in-memory, per-IP)
# ---------------------------------------------------------------------------

# Stores: ip -> list of request timestamps
_rate_limit_store: dict[str, list[float]] = defaultdict(list)

# Config — Iron Shield: stricter auth limits, tier-based chat
RATE_LIMIT_MAX_REQUESTS = 5   # max requests per window
RATE_LIMIT_WINDOW_SEC = 60    # window size in seconds
RATE_LIMIT_PATHS = ("/api/auth/login", "/api/auth/register", "/api/auth/refresh")

# Shield 3: Login lockout after too many attempts (5 per 15 min)
_login_lockout_store: dict[str, float] = {}  # ip -> lockout_until timestamp
LOGIN_LOCKOUT_DURATION = 1800  # 30 minutes
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SEC = 900  # 15 minutes

# Endpoint-specific limits (path_prefix -> max_per_minute)
ENDPOINT_RATE_LIMITS: dict[str, int] = {
    "/api/auth/login": 5,
    "/api/auth/register": 3,
    "/api/auth/refresh": 10,
    "/api/auth/send-magic-link": 3,
    "/api/chat": 30,
    "/api/chat/guest": 10,
    "/api/quiz/generate": 10,
    "/api/quiz/check": 20,
    "/api/iq-test": 10,
    "/api/ocr": 15,
    "/api/voice": 15,
    "/api/research": 10,
    "/api/abitur": 10,
}

# Multiplier for authenticated users (5x the normal limit)
AUTH_RATE_LIMIT_MULTIPLIER = 5

# Owner emails get no rate limiting at all
OWNER_EMAILS_FOR_RATE_LIMIT = {
    "songoku1callme@gmail.com",
    "alkhalaf.ahmad.b@gmail.com",
    "ahmadalkhalaf@protonmail.com",
    "ahmad@lumnos.de",
    "admin@lumnos.de",
}


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


# Per-endpoint rate limit stores
_endpoint_stores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))


def _is_endpoint_rate_limited(ip: str, path: str, is_authenticated: bool = False) -> bool:
    """Check endpoint-specific rate limit.

    Authenticated users get AUTH_RATE_LIMIT_MULTIPLIER times the normal limit.
    """
    for prefix, max_req in ENDPOINT_RATE_LIMITS.items():
        if path.startswith(prefix):
            effective_max = max_req * AUTH_RATE_LIMIT_MULTIPLIER if is_authenticated else max_req
            now = time.monotonic()
            store = _endpoint_stores[prefix]
            window_start = now - RATE_LIMIT_WINDOW_SEC
            store[ip] = [t for t in store[ip] if t > window_start]
            if len(store[ip]) >= effective_max:
                return True
            store[ip].append(now)
            return False
    return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Shield 3: Rate-limit endpoints per IP with login lockout.

    Relax rate limits for authenticated users (AUTH_RATE_LIMIT_MULTIPLIER).
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        path = request.url.path
        ip = _client_ip(request)

        # Determine whether this request is authenticated (Bearer token present)
        auth_header = request.headers.get("authorization", "")
        is_authenticated = auth_header.startswith("Bearer ") and len(auth_header) > 10

        # Never rate-limit health/ping endpoints
        if path in ("/health", "/healthz", "/api/ping"):
            return await call_next(request)

        # Don't rate limit common bootstrapping auth endpoints
        if path in ("/api/auth/me", "/api/auth/clerk-config"):
            return await call_next(request)

        # Shield 3: Check login lockout first (only applies to login endpoint)
        if path.startswith("/api/auth/login"):
            lockout_until = _login_lockout_store.get(ip, 0)
            if time.monotonic() < lockout_until:
                remaining = int(lockout_until - time.monotonic())
                logger.warning("Login lockout active for IP %s (%ds remaining)", ip, remaining)
                return JSONResponse(
                    status_code=429,
                    content={"detail": f"Zu viele Login-Versuche. Gesperrt für {remaining // 60} Minuten."},
                    headers={"Retry-After": str(remaining)},
                )

        # Check endpoint-specific limits (authenticated users get relaxed limits)
        if _is_endpoint_rate_limited(ip, path, is_authenticated=is_authenticated):
            logger.warning(
                "Rate limit exceeded for IP %s on %s (auth=%s)", ip, path, is_authenticated
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Zu viele Anfragen. Bitte warte einen Moment."},
                headers={"Retry-After": "60"},
            )

        # Legacy fallback for auth endpoints
        if any(path.startswith(p) for p in RATE_LIMIT_PATHS):
            if _is_rate_limited(ip):
                # Trigger lockout for login endpoint
                if path.startswith("/api/auth/login"):
                    _login_lockout_store[ip] = time.monotonic() + LOGIN_LOCKOUT_DURATION
                    logger.warning("Login lockout triggered for IP %s", ip)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Zu viele Anfragen. Bitte warte einen Moment."},
                    headers={"Retry-After": "60"},
                )

        return await call_next(request)


# ---------------------------------------------------------------------------
# Security Headers
# ---------------------------------------------------------------------------

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Shield 6: Hardened security headers on every response."""

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
        # Allow camera (OCR) and microphone (Speech-to-Text) from same origin
        response.headers["Permissions-Policy"] = (
            "camera=(self), microphone=(self), geolocation=()"
        )
        # Shield 6: Strict-Transport-Security for HTTPS
        if not os.getenv("LUMNOS_DEV_MODE"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


# ---------------------------------------------------------------------------
# Shield 10: Request Body Size Limiter
# ---------------------------------------------------------------------------

MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Shield 10: Reject requests with body larger than MAX_BODY_SIZE."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_SIZE:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body zu gross (max 10 MB)."},
            )
        return await call_next(request)


# ---------------------------------------------------------------------------
# Shield 10: Bot Protection (User-Agent validation)
# ---------------------------------------------------------------------------

BLOCKED_USER_AGENTS = [
    "scrapy", "python-urllib", "curl/", "wget/", "httpclient",
    "go-http-client", "java/", "libwww-perl",
]


class BotProtectionMiddleware(BaseHTTPMiddleware):
    """Shield 10: Block known scraper/bot user agents."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        # Skip for health checks, ping, and public endpoints
        path = request.url.path
        if path in ("/health", "/healthz", "/api/ping", "/docs", "/openapi.json"):
            return await call_next(request)

        # Don't block WebSocket handshakes
        if path.startswith("/ws/") or path.startswith("/api/notifications/ws/") or path.startswith("/api/multiplayer/ws/"):
            return await call_next(request)

        user_agent = (request.headers.get("user-agent") or "").lower()

        # Block requests with no user-agent on API endpoints
        if not user_agent and path.startswith("/api/"):
            logger.warning("Blocked request with no user-agent on %s", path)
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden"},
            )

        # Block known scraper agents
        for bot in BLOCKED_USER_AGENTS:
            if bot in user_agent:
                logger.warning("Blocked bot user-agent: %s on %s", user_agent[:80], path)
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Forbidden"},
                )

        return await call_next(request)


# ---------------------------------------------------------------------------
# CORS allowed origins
# ---------------------------------------------------------------------------

# Allowed frontend origins — extend as needed
ALLOWED_ORIGINS = [
    "https://mass-mash.vercel.app",
    "https://lumnos-german-tutor-app-mzmkkhlp.devinapps.com",
    "https://mass-mash-git-devin-1772317-607977-songoku1callme-devs-projects.vercel.app",
    "https://massmash.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:5175",
]
