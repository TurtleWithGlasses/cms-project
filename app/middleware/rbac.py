from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from app.utils.auth_helpers import get_current_user
from app.database import get_db
from app.models.user import Role  # Import the Role model
from fastapi.dependencies.utils import run_in_threadpool
from contextlib import contextmanager

@contextmanager
def db_context():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

class RBACMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_roles=None):
        super().__init__(app)
        self.allowed_roles = allowed_roles or []

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        public_paths = ["/docs", "/openapi.json", "/login", "/register", "/users/me", "/token"]
        if request.url.path in public_paths:
            return await call_next(request)

        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        print(f"Authorization Header: {request.headers.get('Authorization')}")

        if not token:
            if request.url.path not in public_paths:
                raise HTTPException(status_code=401, detail="Authentication token is required")
            return await call_next(request)

        try:
            with db_context() as db:
                user = await run_in_threadpool(get_current_user, token, db)
                print(f"Authenticated user: {user.username}, Role ID: {user.role_id}")

                # Query the role name from the Role table using role_id
                role_name = db.query(Role.name).filter(Role.id == user.role_id).scalar()

                if not role_name or role_name not in self.allowed_roles:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Role '{role_name if role_name else 'None'}' not authorized for this resource",
                    )

                print(f"User Role: {role_name}")
                print(f"Allowed Roles: {self.allowed_roles}")
                return await call_next(request)
        except HTTPException as e:
            print(f"Authorization error: {e.detail}")
            raise e
        except Exception as e:
            print(f"Unexpected error in RBACMiddleware: {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")
