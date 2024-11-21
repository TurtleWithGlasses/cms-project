from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.content import Content
from app.models.notification import Notification, NotificationStatus
from app.schemas.content import ContentResponse
from app.utils.activity_log import log_activity
from app.utils.auth_helpers import get_current_user
from app.permissions_config.permissions import ROLE_PERMISSIONS
from app.models.user import Role
from app.models.activity_log import ActivityLog
from app.schemas.notifications import PaginatedNotifications, MarkAllNotificationsReadRequest

from ..schemas import UserCreate, UserResponse, UserUpdate, RoleUpdate
from ..models import User
from ..database import get_db
from ..auth import get_role_validator, hash_password

router = APIRouter()

def get_role_name(role_id: int, db: Session) -> str:
    """
    Helper function to fetch role name from the database using role_id.
    """
    role_name = db.query(Role.name).filter(Role.id == role_id).scalar()
    if not role_name:
        raise HTTPException(status_code=500, detail="Role not found for the user")
    return role_name


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register_user(user: UserCreate, request: Request, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists",
        )

    default_role = db.query(Role).filter(Role.name == "user").first()
    if not default_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default role 'user' not found in the database",
        )

    hashed_password = hash_password(user.password)
    new_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        role_id=default_role.id,
    )
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while saving the user. Please try again later.",
        )

    log_activity(
        db=db,
        user_id=new_user.id,
        action="user_registration",
        description="New user registered",
        details={"username": user.username, "email": user.email},
        # ip_address=request.client.host
    )

    return {
        "id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "role": default_role.name,
    }


@router.get("/users/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role_name = get_role_name(current_user.role_id, db)
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": role_name,
    }

@router.get("/users", response_model=List[UserResponse], dependencies=[Depends(get_role_validator(["admin", "superadmin"]))])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    response = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": get_role_name(user.role_id, db),
        }
        for user in users
    ]
    return response

@router.patch("/users/me", response_model=UserResponse)
def update_user_profile(user_data: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    editor_role_id = db.query(Role.id).filter(Role.name == "editor").scalar()
    if current_user.role_id == editor_role_id and (user_data.email or user_data.username):
        raise HTTPException(status_code=403, detail="Editors cannot change email or username")

    if user_data.email:
        current_user.email = user_data.email
        log_activity(
            db=db,
            action="email_update",
            user_id=current_user.id,
            description=f"User updated their email to {user_data.email}",
        )
    
    if user_data.username:
        current_user.username = user_data.username
        log_activity(
            db=db,
            action="username_update",
            user_id=current_user.id,
            description=f"User updated their username to {user_data.username}",
        )

    if user_data.password:
        current_user.hashed_password = hash_password(user_data.password)
        log_activity(
            db=db,
            action="password_update",
            user_id=current_user.id,
            description="User updated their password",
        )

    db.commit()
    db.refresh(current_user)

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": get_role_name(current_user.role_id, db),
    }

@router.post("/users/admin", response_model=UserResponse, dependencies=[Depends(get_role_validator(["superadmin"]))])
def create_admin(user_data: UserCreate, db: Session = Depends(get_db)):
    admin_role_id = db.query(Role.id).filter(Role.name == "admin").scalar()
    new_admin = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
        role_id=admin_role_id,
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return {
        "id": new_admin.id,
        "username": new_admin.username,
        "email": new_admin.email,
        "role": "admin",
    }

@router.put("/users/{user_id}/role", response_model=UserResponse, dependencies=[Depends(get_role_validator(["admin"]))])
def update_user_role(user_id: int, role_data: RoleUpdate, db: Session = Depends(get_db)):
    user_to_update = db.query(User).filter(User.id == user_id).first()
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")
    
    role_id = db.query(Role.id).filter(Role.name == role_data.role).scalar()
    if not role_id:
        raise HTTPException(status_code=400, detail="Invalid role provided")

    user_to_update.role_id = role_id
    db.commit()
    db.refresh(user_to_update)

    log_activity(
        db=db,
        action="role_update",
        user_id=user_to_update.id,
        description=f"Updated role to {role_data.role}",
    )

    return {
        "id": user_to_update.id,
        "username": user_to_update.username,
        "email": user_to_update.email,
        "role": role_data.role,
    }

@router.get("/user/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": get_role_name(user.role_id, db),
    }

@router.delete("/users/{user_id}", status_code=200, dependencies=[Depends(get_role_validator(["admin", "superadmin"]))])
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not current_user or not current_user.id:
        raise HTTPException(status_code=400, detail="Invalid current user")

    # Log the delete activity
    log_activity(
        db=db,
        action="delete_user",
        user_id=current_user.id,
        description=f"Deleted user {user_to_delete.username} (ID: {user_to_delete.id})",
        details={
            "username": user_to_delete.username,
            "email": user_to_delete.email,
            "deleted_by": current_user.username,
        },
    )

    db.query(ActivityLog).filter(ActivityLog.user_id == user_to_delete.id).update({"user_id": None})
    db.commit()

    try:
        db.delete(user_to_delete)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")

    return {
        "message": f"User {user_to_delete.username} (ID: {user_to_delete.id}) has been successfully deleted."
    }

@router.get("/secure-endpoint", dependencies=[Depends(get_role_validator(["admin", "editor"]))])
def secure_endpoint():
    return {"message": "You have permission to access this resource."}

@router.get("/admin-only", dependencies=[Depends(get_role_validator(["admin"]))], status_code=status.HTTP_200_OK)
def admin_only_endpoint():
    """
    This endpoint is restricted to admin users only.
    """
    return {"message": "This is restricted to admins only."}

@router.get("/logs", dependencies=[Depends(get_role_validator(["admin","superadmin"]))])
def get_activity_logs(db: Session = Depends(get_db)):
    logs = db.query(ActivityLog).order_by(ActivityLog.timestamp.desc()).all()
    return logs

@router.get("/notifications")
async def get_notifications(status: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if status:
        query = query.filter(Notification.status == status)
    
    notifications = query.all()

    return notifications

@router.get("/fetch_notifications", response_model=PaginatedNotifications)
async def get_all_notifications(
    status: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if page < 1 or size < 1:
        raise HTTPException(status_code=400, detail="Page and size must be greater than 0")
    
    print(f"Filter status: {status}")
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if status:
        try:
            query = query.filter(Notification.status == NotificationStatus[status.upper()])
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    total_notifications = query.count()
    notifications = query.offset((page - 1) * size).limit(size).all()

    return {
        "total": total_notifications,
        "page": page,
        "size": size,
        "notifications": notifications
    }

@router.put("/notifications/read_all", status_code=200)
async def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        unread_notifications = db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.status == NotificationStatus.UNREAD
        ).all()

        if not unread_notifications:
            return {"message": "No unread notifications to mark as read"}

        for notification in unread_notifications:
            notification.status = NotificationStatus.READ

        db.commit()

        return {"message": f"{len(unread_notifications)} notifications marked as read"}

    except Exception as e:
        print(f"Unexpected Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.put("/notifications/{id}")
async def update_notification_status(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notification = db.query(Notification).filter(Notification.id == id, Notification.user_id == current_user.id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.status = NotificationStatus.READ
    db.commit()
    db.refresh(notification)
    return notification


@router.put("/notifications/{notification_id}/read", status_code=200)
async def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.status = NotificationStatus.READ
    db.commit()
    db.refresh(notification)

    return {"message": "Notification marked as read", "notification": notification}

