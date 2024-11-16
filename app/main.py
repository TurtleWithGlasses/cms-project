from fastapi import FastAPI
from app.routes import user, auth
from app.middleware.rbac import RBACMiddleware

app = FastAPI()

app.add_middleware(RBACMiddleware, allowed_roles=["admin", "superadmin"])

app.include_router(user.router)
app.include_router(auth.router)

@app.get("/")
def read_root():
    return {"message": "App is running"}
