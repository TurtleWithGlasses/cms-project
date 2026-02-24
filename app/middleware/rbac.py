import logging

from fastapi import HTTPException, Request
from pydantic import ValidationError
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, RedirectResponse

from app.auth import get_current_user
from app.database import AsyncSessionLocal
from app.models.user import Role

logger = logging.getLogger(__name__)


class RBACMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_roles=None):
        super().__init__(app)
        self.allowed_roles = allowed_roles or []
        self.public_paths = {
            "/",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/login",
            "/logout",
            "/register",
            "/api/v1/users/register",
            "/auth/token",
            "/token",
            "/favicon.ico",
            "/graphql",
            "/developer",
            "/api/v1/developer/changelog",
            # Monitoring endpoints — must be reachable by Prometheus and k8s probes
            "/health",
            "/ready",
            "/health/detailed",
            "/metrics",
            "/metrics/summary",
            # Security & privacy — public informational endpoints
            "/api/v1/policy-version",
            "/api/v1/security/headers",
            # WebSocket monitoring — public (Prometheus / health checks)
            "/api/v1/ws/stats",
            "/api/v1/ws/presence",
        }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        logger.debug(f"Processing request for path: {request.url.path}")
        logger.debug(f"Request Method: {request.method}")
        logger.debug(f"Request Headers: {request.headers}")

        # Allow public paths
        if request.url.path in self.public_paths:
            return await call_next(request)

        # Allow static assets (for frontend)
        if request.url.path.startswith("/assets/") or request.url.path.endswith(
            (".js", ".css", ".svg", ".png", ".jpg", ".ico", ".woff", ".woff2", ".ttf")
        ):
            return await call_next(request)

        # Allow public API paths (social sharing, analytics config, i18n metadata)
        if (
            request.url.path.startswith("/api/v1/social/")
            or request.url.path == "/api/v1/analytics/config"
            or request.url.path.startswith("/api/v1/i18n/")
        ):
            return await call_next(request)

        # Allow requests authenticated via API key — route-level dependency validates them
        x_api_key = request.headers.get("X-API-Key")
        token = request.cookies.get("access_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token and not x_api_key:
            return RedirectResponse(url="/login")
        if not token and x_api_key:
            return await call_next(request)

        if token.startswith("Bearer "):
            token = token[len("Bearer ") :]

        # Manually create the DB session
        async with AsyncSessionLocal() as db:
            try:
                user = await get_current_user(request=request, db=db)
                logger.info(f"Authenticated user: {user.username}, Role ID: {user.role_id}")

                # Fetch the role name
                result = await db.execute(select(Role.name).where(Role.id == user.role_id))
                role_name = result.scalar()

                if not role_name or role_name not in self.allowed_roles:
                    logger.error(f"Role '{role_name if role_name else 'None'}' not authorized for this resource")
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": f"Role '{role_name if role_name else 'None'}' not authorized for this resource"
                        },
                    )

                return await call_next(request)

            except HTTPException as e:
                logger.error(f"Authorization error: {e.detail}")
                return JSONResponse(status_code=e.status_code, content={"detail": str(e.detail)})

            except ValidationError as e:
                logger.error(f"Validation error: {e.json()}")
                return JSONResponse(status_code=422, content={"detail": e.errors()})

            except Exception as e:
                logger.error(f"Unhandled middleware exception: {str(e)}")
                return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
