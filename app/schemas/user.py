from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.utils.sanitize import sanitize_email, sanitize_username


class RoleEnum(str, Enum):
    admin = "admin"
    user = "user"
    manager = "manager"
    superadmin = "superadmin"


class UserCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str = Field(..., min_length=3, max_length=50, description="Username must be between 3 and 50 characters.")
    password: str = Field(..., min_length=8, max_length=128, description="Password must be at least 8 characters long.")
    email: EmailStr = Field(..., description="A valid email address.")

    @field_validator("username")
    @classmethod
    def sanitize_username_field(cls, v):
        """Sanitize username - remove HTML and special characters"""
        sanitized = sanitize_username(v)
        if len(sanitized) < 3:
            raise ValueError("Username must be at least 3 characters after sanitization")
        return sanitized

    @field_validator("email")
    @classmethod
    def sanitize_email_field(cls, v):
        """Sanitize email - basic cleanup"""
        return sanitize_email(v)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength - requires uppercase, lowercase, and digit"""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str


class UserUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str | None = Field(
        None, min_length=3, max_length=50, description="Username must be between 3 and 50 characters."
    )
    email: EmailStr | None = Field(None, description="A valid email address.")
    password: str | None = Field(
        None, min_length=8, max_length=128, description="Password must be at least 8 characters long."
    )

    @field_validator("username")
    @classmethod
    def sanitize_username_field(cls, v):
        """Sanitize username - remove HTML and special characters"""
        if v is None:
            return v
        sanitized = sanitize_username(v)
        if sanitized and len(sanitized) < 3:
            raise ValueError("Username must be at least 3 characters after sanitization")
        return sanitized

    @field_validator("email")
    @classmethod
    def sanitize_email_field(cls, v):
        """Sanitize email - basic cleanup"""
        return sanitize_email(v) if v else v

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength - requires uppercase, lowercase, and digit"""
        if v is None:
            return v
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class RoleUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: RoleEnum

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in RoleEnum:
            raise ValueError(f"Invalid role: {v}")
        return v


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
