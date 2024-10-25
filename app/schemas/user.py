from pydantic import BaseModel
from typing import Optional
from enum import Enum

class UserCreate(BaseModel):
    username: str
    password: str
    email: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str

    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None

    class Config:
        orm_mode = True

class RoleUpdate(BaseModel):
    role: str

    class Config:
        orm_mode = True

class RoleEnum(str, Enum):
    admin = "admin"
    user = "user"
    manager = "manager"
    superadmin = "superadmin"

class RoleUpdate(BaseModel):
    role: RoleEnum
