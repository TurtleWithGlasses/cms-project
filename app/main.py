import logging
from fastapi import FastAPI
from app.routes import user, auth, roles, category, password_reset
from app.routes.content import router as content_router
from app.database import engine, Base
from app.middleware.rbac import RBACMiddleware

logging.basicConfig()
# logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

app = FastAPI()

app.add_middleware(
    RBACMiddleware,
    allowed_roles=["user", "admin", "superadmin"]
)

# Include routers with API versioning
# API v1 routes (standardized)
app.include_router(user.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(roles.router, prefix="/api/v1/roles", tags=["Roles"])
app.include_router(content_router, prefix="/api/v1/content", tags=["Content"])
app.include_router(category.router, prefix="/api/v1/categories", tags=["Categories"])
app.include_router(password_reset.router, prefix="/api/v1/password-reset", tags=["Password Reset"])

# Auth routes (keep at /auth for OAuth2 compatibility)
app.include_router(auth.router, prefix="/auth", tags=["Auth"])

# Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "Welcome to the CMS API"}
