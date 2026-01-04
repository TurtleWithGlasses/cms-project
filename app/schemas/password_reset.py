"""
Password Reset Schemas

Pydantic models for password reset requests and responses.
"""

from pydantic import BaseModel, EmailStr, Field, validator


class PasswordResetRequest(BaseModel):
    """Schema for password reset request"""
    email: EmailStr = Field(..., description="User's email address")


class PasswordResetConfirm(BaseModel):
    """Schema for confirming password reset with token"""
    token: str = Field(..., min_length=1, description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")
    confirm_password: str = Field(..., min_length=8, max_length=100, description="Confirm new password")

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Validate that passwords match"""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class PasswordResetResponse(BaseModel):
    """Schema for password reset response"""
    message: str
    success: bool = True
