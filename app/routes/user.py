from fastapi import APIRouter, Depends, HTTPException, status, Request
import logging
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, text
from typing import List, Optional

from app.models.content import Content
from app.models.notification import Notification, NotificationStatus
from app.schemas.content import ContentResponse
from app.utils.activity_log import log_activity
from app.utils.auth_helpers import get_current_user
from app.permissions_config.permissions import ROLE_PERMISSIONS
from app.models.user import Role, RoleEnum
from app.models.activity_log import ActivityLog
from app.schemas.notifications import PaginatedNotifications, MarkAllNotificationsReadRequest

from app.schemas import UserCreate, UserResponse, UserUpdate, RoleUpdate
from app.models import User
from app.database import get_db
from app.auth import get_role_validator, hash_password

router = APIRouter()

async def get_role_name(role_id: int, db: AsyncSession) -> str:
    query = select(Role.name).where(Role.id == role_id)
    result = await db.execute(query)
    role_name = result.scalar()
    if not role_name:
        raise HTTPException(status_code=500, detail="Role not found for the user")
    return role_name

@router.get("/users/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    role_name = await get_role_name(current_user.role_id, db)
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": role_name,
    }

@router.get("/users", response_model=List[UserResponse], dependencies=[Depends(get_role_validator(["admin", "superadmin"]))])
async def list_users(db: AsyncSession = Depends(get_db)):
    query = select(User)
    result = await db.execute(query)
    users = result.scalars().all()
    response = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": await get_role_name(user.role_id, db),
        }
        for user in users
    ]
    return response

@router.put("/users/{user_id}/role", response_model=UserResponse, dependencies=[Depends(get_role_validator(["admin"]))])
async def update_user_role(user_id: int, role_data: RoleUpdate, db: AsyncSession = Depends(get_db)):
    logging.info(f"Received request to update user_id: {user_id} to role: {role_data.role}")

    # Step 1: Fetch the user
    result = await db.execute(select(User).where(User.id == user_id))
    user_to_update = result.scalar()

    if not user_to_update:
        logging.error(f"User not found: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")

    # Step 2: Validate the role
    result = await db.execute(
        text("SELECT id FROM roles WHERE name = :role_name"), {"role_name": role_data.role}
    )
    role_id = result.scalar()
    if not role_id:
        logging.error(f"Invalid role: {role_data.role}")
        raise HTTPException(status_code=400, detail="Invalid role provided")

    # Step 3: Update the user's role
    logging.info(f"Updating user_id: {user_id} to role_id: {role_id}")
    user_to_update.role_id = role_id

    try:
        await db.commit()
        await db.refresh(user_to_update)
        logging.info(f"User updated successfully: {user_to_update}")
    except Exception as e:
        logging.error(f"Failed to update role: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update role: {str(e)}")

    # Step 4: Log the activity with a new session
    try:
        async with db.bind.connect() as connection:
            new_session = AsyncSession(bind=connection)
            await log_activity(
                db=new_session,
                action="role_update",
                user_id=user_to_update.id,
                description=f"Updated role to {role_data.role}",
            )
            await new_session.commit()  # Commit the log activity
    except Exception as log_error:
        logging.error(f"Failed to log activity: {log_error}")
        # Proceed with the response, even if logging fails

    # Step 5: Return the updated user
    return {
        "id": user_to_update.id,
        "username": user_to_update.username,
        "email": user_to_update.email,
        "role": role_data.role,
    }


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name in ["admin", "superadmin"]:
        pass
    elif user_id == current_user.id:
        pass
    else:
        raise HTTPException(status_code=403, detail="You can only update your own details")
    # Fetch user from the database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_update_data.username:
        user.username = user_update_data.username
    if user_update_data.email:
        user.email = user_update_data.email
    if user_update_data.password:
        user.hashed_password = hash_password(user_update_data.password)

    try:
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update user: " + str(e))

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role.name,
    }

@router.post("/users/admin", response_model=UserResponse, dependencies=[Depends(get_role_validator(["superadmin"]))])
async def create_admin(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Wrap the raw SQL query with `text`
    query = text("SELECT id FROM roles WHERE name = :role_name")
    result = await db.execute(query, {"role_name": "admin"})
    admin_role_id = result.scalar()
    
    if not admin_role_id:
        raise HTTPException(status_code=500, detail="Admin role not found")
    
    new_admin = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
        role_id=admin_role_id,
    )
    db.add(new_admin)
    try:
        await db.commit()
        await db.refresh(new_admin)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create admin: {str(e)}")
    
    return {
        "id": new_admin.id,
        "username": new_admin.username,
        "email": new_admin.email,
        "role": "admin",
    }

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def register_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check for existing user
    result = await db.execute(
        select(User).where((User.username == user.username) | (User.email == user.email))
    )
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists",
        )

    # Fetch the default role and preload attributes
    result = await db.execute(select(Role).where(Role.name == "user"))
    default_role = result.scalars().first()

    if not default_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default role 'user' not found in the database",
        )

    # Access `default_role.name` safely
    default_role_name = default_role.name

    # Create new user
    hashed_password = hash_password(user.password)
    new_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        role_id=default_role.id,
    )
    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while saving the user: {str(e)}",
        )

    return {
        "id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "role": default_role_name,  # This is now safe
    }

@router.patch("/me", response_model=UserResponse)
async def update_user_profile(user_data: UserUpdate,
                              current_user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_db)
                              ):
    result = await db.execute("SELECT id FROM roles WHERE name = :role_name", {"role_name": "editor"})
    editor_role_id = result.scalar()
    if current_user.role_id == editor_role_id and (user_data.email or user_data.username):
        raise HTTPException(status_code=403, detail="Editors cannot change email or username")

    if user_data.email:
        current_user.email = user_data.email
        await log_activity(
            db=db,
            action="email_update",
            user_id=current_user.id,
            description=f"User updated their email to {user_data.email}",
        )
    
    if user_data.username:
        current_user.username = user_data.username
        await log_activity(
            db=db,
            action="username_update",
            user_id=current_user.id,
            description=f"User updated their username to {user_data.username}",
        )

    if user_data.password:
        current_user.hashed_password = hash_password(user_data.password)
        await log_activity(
            db=db,
            action="password_update",
            user_id=current_user.id,
            description="User updated their password",
        )

    await db.commit()
    await db.refresh(current_user)

    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": await get_role_name(current_user.role_id, db),
    }

@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    # Fetch user by ID
    result = await db.execute("SELECT * FROM users WHERE id = :user_id", {"user_id": user_id})
    user = result.scalar()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role_name = await get_role_name(user.role_id, db)

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": role_name,
    }

@router.put("/users/{user_id}/role", response_model=UserResponse, dependencies=[Depends(get_role_validator(["admin"]))])
async def update_user_role(user_id: int, role_data: RoleUpdate, db: AsyncSession = Depends(get_db)):
    logging.info(f"Received request to update user_id: {user_id} to role: {role_data.role}")

    result = await db.execute(select(User).where(User.id == user_id))
    user_to_update = result.scalar()

    if not user_to_update:
        logging.error(f"User not found: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        text("SELECT id FROM roles WHERE name = :role_name"), {"role_name": role_data.role}
    )
    role_id = result.scalar()
    if not role_id:
        logging.error(f"Invalid role: {role_data.role}")
        raise HTTPException(status_code=400, detail="Invalid role provided")

    logging.info(f"Updating user_id: {user_id} to role_id: {role_id}")
    user_to_update.role_id = role_id

    try:
        await db.commit()
        await db.refresh(user_to_update)
        logging.info(f"User updated successfully: {user_to_update}")
    except Exception as e:
        logging.error(f"Failed to update role: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update role: {str(e)}")

    return {
        "id": user_to_update.id,
        "username": user_to_update.username,
        "email": user_to_update.email,
        "role": role_data.role,
    }


@router.delete("/users/{user_id}", status_code=200, dependencies=[Depends(get_role_validator(["admin", "superadmin"]))])
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Fetch user to delete
    result = await db.execute("SELECT * FROM users WHERE id = :user_id", {"user_id": user_id})
    user_to_delete = result.scalar()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")

    # Log delete activity
    await log_activity(
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

    # Nullify related logs and delete the user
    await db.execute("UPDATE activity_logs SET user_id = NULL WHERE user_id = :user_id", {"user_id": user_to_delete.id})
    try:
        await db.delete(user_to_delete)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")

    return {
        "message": f"User {user_to_delete.username} (ID: {user_to_delete.id}) has been successfully deleted."
    }

@router.get("/notifications")
async def get_notifications(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Notification).where(Notification.user_id == current_user.id)

    if status:
        query = query.where(Notification.status == status)

    result = await db.execute(query)
    notifications = result.scalars().all()

    return notifications

@router.get("/fetch_notifications", response_model=PaginatedNotifications)
async def get_all_notifications(
    status: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if page < 1 or size < 1:
        raise HTTPException(status_code=400, detail="Page and size must be greater than 0")

    query = select(Notification).where(Notification.user_id == current_user.id)

    if status:
        try:
            query = query.where(Notification.status == NotificationStatus[status.upper()])
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    total_notifications_result = await db.execute(query)
    total_notifications = len(total_notifications_result.scalars().all())

    paginated_query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(paginated_query)
    notifications = result.scalars().all()

    return {
        "total": total_notifications,
        "page": page,
        "size": size,
        "notifications": notifications,
    }
@router.put("/notifications/read_all", status_code=200)
async def mark_all_notifications_as_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = update(Notification).where(
        Notification.user_id == current_user.id,
        Notification.status == NotificationStatus.UNREAD,
    ).values(status=NotificationStatus.READ)

    result = await db.execute(query)
    await db.commit()

    affected_rows = result.rowcount
    return {"message": f"{affected_rows} notifications marked as read"}

@router.put("/notifications/unread_all", status_code=200)
async def mark_all_notifications_as_unread(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = update(Notification).where(
        Notification.user_id == current_user.id,
        Notification.status == NotificationStatus.READ,
    ).values(status=NotificationStatus.UNREAD)

    result = await db.execute(query)
    await db.commit()

    affected_rows = result.rowcount
    return {"message": f"{affected_rows} notifications marked as unread"}

@router.put("/notifications/{id}")
async def update_notification_status(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Notification).where(
        Notification.id == id, Notification.user_id == current_user.id
    )
    result = await db.execute(query)
    notification = result.scalar()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.status = NotificationStatus.READ
    try:
        await db.commit()
        await db.refresh(notification)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update notification: {str(e)}")

    return notification

@router.put("/notifications/{notification_id}/read", status_code=200)
async def mark_notification_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    )
    result = await db.execute(query)
    notification = result.scalar()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.status = NotificationStatus.READ
    try:
        await db.commit()
        await db.refresh(notification)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to mark notification as read: {str(e)}")

    return {"message": "Notification marked as read", "notification": notification}

@router.put("/notifications/{notification_id}/unread", status_code=200)
async def mark_notification_as_unread(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    )
    result = await db.execute(query)
    notification = result.scalar()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.status = NotificationStatus.UNREAD
    try:
        await db.commit()
        await db.refresh(notification)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to mark notification as unread: {str(e)}")

    return {"message": "Notification marked as unread", "notification": notification}

@router.get("/logs", dependencies=[Depends(get_role_validator(["admin", "superadmin"]))])
async def get_activity_logs(db: AsyncSession = Depends(get_db)):
    result = await db.execute("SELECT * FROM activity_logs ORDER BY timestamp DESC")
    logs = result.scalars().all()
    return logs

@router.get("/secure-endpoint", dependencies=[Depends(get_role_validator(["admin", "editor"]))])
def secure_endpoint():
    return {"message": "You have permission to access this resource."}

@router.get("/admin-only", dependencies=[Depends(get_role_validator(["admin"]))], status_code=status.HTTP_200_OK)
def admin_only_endpoint():
    """
    This endpoint is restricted to admin users only.
    """
    return {"message": "This is restricted to admins only."}