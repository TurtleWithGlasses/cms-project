from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional
from enum import Enum


class RoleEnum(str, Enum):
    admin = "admin"
    user = "user"
    manager = "manager"
    superadmin = "superadmin"


class UserCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str = Field(..., min_length=3, max_length=50, description="Username must be between 3 and 50 characters.")
    password: str = Field(..., min_length=6, max_length=128, description="Password must be between 6 and 128 characters.")
    email: EmailStr = Field(..., description="A valid email address.")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str


class UserUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Username must be between 3 and 50 characters.")
    email: Optional[EmailStr] = Field(None, description="A valid email address.")
    password: Optional[str] = Field(None, min_length=6, max_length=128, description="Password must be between 6 and 128 characters.")


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