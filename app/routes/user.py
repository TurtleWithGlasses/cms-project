from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..schemas import UserCreate, UserResponse, UserUpdate, RoleUpdate
from ..models import User
from ..database import get_db
from ..auth import hash_password, decode_access_token
from app.auth import oauth2_scheme

router = APIRouter()

# Utility function for role permission checks
def has_permission(role: str, allowed_roles: List[str]) -> bool:
    return role in allowed_roles

# User registration route
@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter((User.username == user.email) | (User.username == user.username)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    hashed_password = hash_password(user.password)
    new_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# Get current user function
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        email = decode_access_token(token)
    except HTTPException as e:
        raise e
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# Utility function to check roles
def check_role(current_user: User, required_roles: List[str]):
    if current_user.role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action."
        )

# Get current authenticated user
@router.get("/users/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user

# List users (admin only)
@router.get("/users", response_model=List[UserResponse])
def list_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_role(current_user, ["admin", "superadmin"])
    users = db.query(User).all()
    return users

# Delete user (superadmin only)
@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete users")
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found.")
    db.delete(user_to_delete)
    db.commit()
    return {"message": "User deleted successfully"}

# Update user profile (editor cannot change email/username)
@router.patch("/users/me", response_model=UserResponse)
def update_user_profile(user_data: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == "editor" and (user_data.email or user_data.username):
        raise HTTPException(status_code=403, detail="Editors cannot change email or username")
    if user_data.email:
        current_user.email = user_data.email
    if user_data.username:
        current_user.username = user_data.username
    if user_data.password:
        current_user.hashed_password = hash_password(user_data.password)
    db.commit()
    db.refresh(current_user)
    return current_user

# Update user role (superadmin only)
@router.put("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(user_id: int, role_data: RoleUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can promote users.")

    user_to_update = db.query(User).filter(User.id == user_id).first()
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")
    
    if role_data.role == "superadmin" and user_to_update.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can be promoted to superadmin.")
    user_to_update.role = role_data.role
    db.commit()
    db.refresh(user_to_update)
    return user_to_update

# Create a new admin (superadmin only)
@router.post("/users/admin", response_model=UserResponse)
def create_admin(user_data: UserCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    check_role(current_user, ["superadmin"])
    new_admin = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
        role="admin"
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return new_admin
