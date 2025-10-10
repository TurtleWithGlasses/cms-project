import logging
from fastapi import FastAPI
from app.routes import user, auth
from app.database import engine, Base
from app.middleware.rbac import RBACMiddleware

logging.basicConfig()
# logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

app = FastAPI()

app.add_middleware(
    RBACMiddleware, 
    allowed_roles=["user", "admin", "superadmin"]
)

# Include routers
app.include_router(user.router)
app.include_router(auth.router)

# Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "Welcome to the CMS API"}
