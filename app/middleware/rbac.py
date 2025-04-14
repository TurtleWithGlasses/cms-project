from pydantic import ValidationError
from sqlalchemy import select
from fastapi import Request, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from app.utils.auth_helpers import get_current_user
from app.database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import Role
import logging

logger = logging.getLogger(__name__)

class RBACMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_roles=None):
        super().__init__(app)
        self.allowed_roles = allowed_roles or []
        self.public_paths = {
            "/",
            "/docs",
            "/openapi.json",
            "/login",
            "/users/register",
            "/register",
            "/users/me",
            "/users/users/me",
            "/users/users",
            "/users/users/admin"
            "/users/token",
            "/token",
            "/auth/token",
            "/admin/dashboard",
            "/favicon.ico"
        }

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        logger.debug(f"Processing request for path: {request.url.path}")
        logger.debug(f"Request Method: {request.method}")
        logger.debug(f"Request Headers: {request.headers}")

        if request.url.path in self.public_paths:
            return await call_next(request)

        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            raise HTTPException(status_code=401, detail="Authentication token is required")

        # Manually create the DB session
        async with AsyncSessionLocal() as db:
            try:
                user = await get_current_user(token=token, db=db)
                logger.info(f"Authenticated user: {user.username}, Role ID: {user.role_id}")

                # Fetch the role name
                result = await db.execute(select(Role.name).where(Role.id == user.role_id))
                role_name = result.scalar()

                if not role_name or role_name not in self.allowed_roles:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Role '{role_name if role_name else 'None'}' not authorized for this resource",
                    )

                return await call_next(request)

            except HTTPException as e:
                logger.error(f"Authorization error: {e.detail}")
                raise e

            except ValidationError as e:
                logger.error(f"Validation error: {e.json()}")
                raise HTTPException(status_code=422, detail=e.errors())
            
            except Exception as e:
                logger.error(f"Unhandled middleware exception: {str(e)}")
                raise HTTPException(status_code=500, detail="Internal Server Error")



