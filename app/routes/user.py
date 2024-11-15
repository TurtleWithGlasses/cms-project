from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.models.content import Content
from app.models.notification import Notification, NotificationStatus
from app.schemas.content import ContentResponse
from app.utils.activity_log import log_activity
from app.utils.auth_helpers import get_current_user
from ..schemas import UserCreate, UserResponse, UserUpdate, RoleUpdate
from ..models import User
from ..database import get_db
from ..auth import hash_password

router = APIRouter()


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
    log_activity(
        db=db,
        action="user_registration",
        user_id=new_user.id,
        description=f"New user registered with username: {new_user.username} and email: {new_user.email}"
    )
    return new_user


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

# Update user profile (editor cannot change email/username)
@router.patch("/users/me", response_model=UserResponse)
def update_user_profile(user_data: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == "editor" and (user_data.email or user_data.username):
        raise HTTPException(status_code=403, detail="Editors cannot change email or username")
    if user_data.email:
        current_user.email = user_data.email
        log_activity(
            db=db,
            action="email_update",
            user_id=current_user.id,
            description=f"User updated their email to {user_data.email}"
        )
    
    if user_data.username:
        current_user.username = user_data.username
        log_activity(
            db=db,
            action="username_update",
            user_id=current_user.id,
            description=f"User updated their username to {user_data.username}"
        )

    if user_data.password:
        current_user.hashed_password = hash_password(user_data.password)
        log_activity(
            db=db,
            action="password_update",
            user_id=current_user.id,
            description="User updated their password"
        )
    db.commit()
    db.refresh(current_user)
    return current_user


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

@router.put("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(user_id: int, role_data: RoleUpdate, current_user: User = Depends(get_current_user), db:Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    user_to_update = db.query(User).filter(User.id == user_id).first()
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_to_update.role = role_data.role
    db.commit()
    db.refresh(user_to_update)

    log_activity(
        db=db,
        action="role_update",
        user_id=current_user.id,
        target_user_id=user_to_update.id,
        description=f"Updated role to {role_data.role}"
    )

    return user_to_update

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete users")
    
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found.")
    
    db.delete(user_to_delete)
    db.commit()
    
    # Log the deletion action
    log_activity(
        db=db,
        action="user_deletion",
        user_id=current_user.id,
        target_user_id=user_to_delete.id,
        description="Deleted user account"
    )

    return {"message": "User deleted successfully"}

@router.get("/content/pending-approvals", response_model=List[ContentResponse])
def get_pending_approvals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in ["admin", "editor"]:
        raise HTTPException(status_code=403, detail="Not authorized to view pending approvals")
    
    pending_content = db.query(Content).filter(Content.status == "PENDING").all()
    return pending_content

@router.patch("/notifications/{notification_id}/mark-read", status_code=status.HTTP_204_NO_CONTENT)
def mark_notification_as_read(notification_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.status = NotificationStatus.READ
    db.commit()
    return {"message": "Notification marked as read"}