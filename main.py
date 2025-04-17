import logging
import uvicorn
from starlette.middleware.sessions import SessionMiddleware
from fastapi import FastAPI, Form, Request, Depends, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.routes import user, auth, roles
from app.database import Base, engine, get_db, get_async_session
from app.middleware.rbac import RBACMiddleware
from app.routes import category
from app.routes.content import router as content_router
from app.config import settings
from app.scheduler import scheduler
from app.services.content_service import get_all_content
from app.services.auth_service import authenticate_user, register_user
from app.models import User
from app.auth import (
    get_current_user,
    create_access_token,
    verify_password,
    hash_password,
    get_current_user_with_role,
    oauth2_scheme
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="templates")

# Configure logging
app = FastAPI(title="CMS Project")

# CORS (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with allowed origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="A custom CMS backend powered by FastAPI",
        debug=settings.debug,
        version=settings.app_version,
    )

    # Add middleware
    app.add_middleware(
        RBACMiddleware,
        allowed_roles=["user", "admin", "superadmin"]
    )
    app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

    # Include routers
    app.include_router(user.router, prefix="/users", tags=["Users"])
    app.include_router(auth.router, prefix="/auth", tags=["Auth"])
    app.include_router(roles.router, prefix="/api", tags=["roles"])
    app.include_router(content_router, prefix="/api/v1", tags=["Content"])
    app.include_router(category.router, prefix="/api", tags=["Categories"])

    if settings.debug:
        logger.info(f"Running in {settings.environment} mode")
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)  # Logs SQL statements
        logging.getLogger("sqlalchemy.pool").setLevel(logging.INFO)  # Logs connection pool checkouts
        logging.getLogger("sqlalchemy.dialects").setLevel(logging.DEBUG)  # Logs SQL dialect-specific queries
        logging.getLogger("sqlalchemy.orm").setLevel(logging.DEBUG) 

    return app

app = create_app()

@app.on_event("startup")
async def startup_event():
    """Tasks to run at application startup."""
    logger.info("Starting up the application...")
    # Perform database initialization or other startup tasks
    if settings.debug:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created (if not existing).")

    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down the application...")

@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to the CMS API"}

@app.get("/register")
async def get_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def post_register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_async_session)
):
    await register_user(username, email, password, db)
    return RedirectResponse("/login", status_code=302)

@app.get("/login")
async def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def post_login(
    response: Response,
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_async_session)
):
    try:
        user = await authenticate_user(username, password, db)
        if not user:
            return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
        
        access_token = create_access_token({"sub": user.username})
        response = RedirectResponse("/profile", status_code=302)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=60 * 60 * 24,
        )
        print("Login successful, redirecting...")
    except HTTPException as e:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": e.detail
            })


    return response

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()  # This clears the user session
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    content_items = await get_all_content(db)
    return templates.TemplateResponse("dashboard.html", {"request": request, "content": content_items})

@app.get("/profile", response_class=HTMLResponse)
async def get_profile(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse("profile.html", {"request": request, "user": current_user})
