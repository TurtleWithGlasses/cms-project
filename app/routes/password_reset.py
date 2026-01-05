"""
Password Reset Routes

Handles password reset request and confirmation endpoints.
"""

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.rate_limit import limiter
from app.schemas.password_reset import PasswordResetConfirm, PasswordResetRequest, PasswordResetResponse
from app.services.password_reset_service import PasswordResetService

router = APIRouter(tags=["Password Reset"])
templates = Jinja2Templates(directory="templates")


@router.get("/request", response_class=HTMLResponse)
async def password_reset_request_form(request: Request):
    """Display password reset request form"""
    return templates.TemplateResponse("password_reset_request.html", {"request": request})


@router.post("/request", response_model=PasswordResetResponse)
@limiter.limit("3/hour")  # Strict rate limit to prevent abuse
async def request_password_reset(request: Request, email: str = Form(...), db: AsyncSession = Depends(get_db)):
    """
    Request a password reset token.

    This endpoint will:
    1. Validate the email
    2. Generate a reset token
    3. Send email with reset link (in production)
    4. Return success message

    Note: Always returns success to prevent email enumeration attacks.
    """
    try:
        reset_token = await PasswordResetService.create_reset_token(email, db)

        # In production, send email here
        # For now, we'll just log the token (DO NOT DO THIS IN PRODUCTION!)
        print(f"Password reset token for {email}: {reset_token.token}")
        print(f"Reset link: http://localhost:8000/api/v1/password-reset/reset?token={reset_token.token}")

        # TODO: Implement email service
        # await email_service.send_password_reset_email(email, reset_token.token)

        return PasswordResetResponse(
            message="If an account exists with this email, a password reset link has been sent.", success=True
        )
    except HTTPException:
        # Return same message regardless of whether email exists
        return PasswordResetResponse(
            message="If an account exists with this email, a password reset link has been sent.", success=True
        )


@router.get("/reset", response_class=HTMLResponse)
async def password_reset_form(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    """Display password reset form with token validation"""
    try:
        # Validate token
        await PasswordResetService.validate_reset_token(token, db)

        return templates.TemplateResponse("password_reset_confirm.html", {"request": request, "token": token})
    except HTTPException as e:
        return templates.TemplateResponse(
            "password_reset_error.html", {"request": request, "error": e.detail}, status_code=e.status_code
        )


@router.post("/reset", response_model=PasswordResetResponse)
@limiter.limit("5/hour")  # Rate limit password reset attempts
async def reset_password(
    request: Request,
    token: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password using a valid token.

    This endpoint will:
    1. Validate the token
    2. Verify password match
    3. Update the user's password
    4. Invalidate the token
    """
    # Validate passwords match
    if new_password != confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    # Validate password length
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters long"
        )

    try:
        # Reset password
        await PasswordResetService.reset_password(token, new_password, db)

        # Redirect to login page with success message
        return RedirectResponse(url="/login?message=Password successfully reset. Please login.", status_code=303)
    except HTTPException as e:
        return templates.TemplateResponse(
            "password_reset_error.html", {"request": request, "error": e.detail}, status_code=e.status_code
        )


# API Endpoints (for frontend applications)
@router.post("/api/request", response_model=PasswordResetResponse)
@limiter.limit("3/hour")
async def api_request_password_reset(
    request: Request, reset_request: PasswordResetRequest, db: AsyncSession = Depends(get_db)
):
    """API endpoint for password reset request"""
    try:
        reset_token = await PasswordResetService.create_reset_token(reset_request.email, db)

        # TODO: Send email with reset link
        # await email_service.send_password_reset_email(reset_request.email, reset_token.token)

        return PasswordResetResponse(
            message="If an account exists with this email, a password reset link has been sent.", success=True
        )
    except HTTPException:
        return PasswordResetResponse(
            message="If an account exists with this email, a password reset link has been sent.", success=True
        )


@router.post("/api/reset", response_model=PasswordResetResponse)
@limiter.limit("5/hour")
async def api_reset_password(request: Request, reset_confirm: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    """API endpoint for password reset confirmation"""
    await PasswordResetService.reset_password(reset_confirm.token, reset_confirm.new_password, db)

    return PasswordResetResponse(
        message="Password successfully reset. You can now login with your new password.", success=True
    )
