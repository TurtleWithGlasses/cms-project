import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.responses import HTMLResponse, RedirectResponse

from app.auth import get_current_user, get_role_validator, hash_password
from app.database import get_db
from app.exceptions import (
    DatabaseError,
    RoleNotFoundError,
    UserNotFoundError,
)
from app.models import User
from app.models.notification import Notification, NotificationStatus
from app.models.user import Role
from app.permissions_config.permissions import get_role_permissions
from app.schemas.notifications import PaginatedNotifications
from app.schemas.user import RoleUpdate, UserCreate, UserResponse, UserUpdate
from app.utils.activity_log import log_activity

router = APIRouter()
templates = Jinja2Templates(directory="templates")


async def get_role_name(role_id: int, db: AsyncSession) -> str:
    query = select(Role.name).where(Role.id == role_id)
    result = await db.execute(query)
    role_name = result.scalar()
    if not role_name:
        raise RoleNotFoundError(role_id)
    return role_name


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    role_name = await get_role_name(current_user.role_id, db)
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": role_name,
    }


@router.get("/", response_model=list[UserResponse], dependencies=[Depends(get_role_validator(["admin", "superadmin"]))])
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


@router.put("/{user_id}/role", response_model=UserResponse, dependencies=[Depends(get_role_validator(["admin"]))])
async def update_user_role(user_id: int, role_data: RoleUpdate, db: AsyncSession = Depends(get_db)):
    logging.info(f"Received request to update user_id: {user_id} to role: {role_data.role}")

    # Step 1: Fetch the user
    result = await db.execute(select(User).where(User.id == user_id))
    user_to_update = result.scalar()

    if not user_to_update:
        logging.error(f"User not found: {user_id}")
        raise UserNotFoundError(user_id)

    # Step 2: Validate the role
    result = await db.execute(text("SELECT id FROM roles WHERE name = :role_name"), {"role_name": role_data.role})
    role_id = result.scalar()
    if not role_id:
        logging.error(f"Invalid role: {role_data.role}")
        raise RoleNotFoundError(role_data.role)

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
        raise DatabaseError(message="Failed to update user role", operation="update_user_role")

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


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.name in ["admin", "superadmin"] or user_id == current_user.id:
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


@router.post("/admin", response_model=UserResponse, dependencies=[Depends(get_role_validator(["superadmin"]))])
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
    result = await db.execute(select(User).where((User.username == user.username) | (User.email == user.email)))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists",
        )

    # Fetch the default role
    result = await db.execute(select(Role).where(Role.name == "user"))
    default_role = result.scalars().first()
    if not default_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default role 'user' not found in the database",
        )

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

        # Log activity after user registration
        await log_activity(
            action="user_register",
            user_id=new_user.id,
            description=f"User {new_user.username} registered successfully.",
        )

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
        "role": default_role.name,
    }


@router.patch("/me", response_model=UserResponse)
async def update_user_profile(
    user_data: UserUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(text("SELECT id FROM roles WHERE name = :role_name"), {"role_name": "editor"})
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
    # Specify the exact columns you need in the query
    query = text("SELECT id, username, email, role_id FROM users WHERE id = :user_id")
    result = await db.execute(query, {"user_id": user_id})
    user = result.fetchone()  # Fetch one row

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Unpack the result based on the columns fetched
    user_id, username, email, role_id = user

    # Get the role name using the role_id
    role_name = await get_role_name(role_id, db)

    # Return the user details in the expected format
    return {
        "id": user_id,
        "username": username,
        "email": email,
        "role": role_name,
    }


@router.delete(
    "/delete/{user_id}",
    status_code=200,
    # dependencies=[Depends(permission_required("delete_user"))]
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user_to_delete = result.scalar_one_or_none()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User to delete not found")

    if user_to_delete.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")

    try:
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
        await db.delete(user_to_delete)
        await db.commit()
        return RedirectResponse(url="/api/v1/users/admin/dashboard", status_code=303)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete user: {str(e)}")


@router.post("/delete/{user_id}")
async def delete_user_post_proxy(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await delete_user(user_id=user_id, db=db, current_user=current_user)


@router.get("/notifications")
async def get_notifications(
    status: str | None = None,
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
    status: str | None = None,
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
    query = (
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.status == NotificationStatus.UNREAD,
        )
        .values(status=NotificationStatus.READ)
    )

    result = await db.execute(query)
    await db.commit()

    affected_rows = result.rowcount
    return {"message": f"{affected_rows} notifications marked as read"}


@router.put("/notifications/unread_all", status_code=200)
async def mark_all_notifications_as_unread(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.status == NotificationStatus.READ,
        )
        .values(status=NotificationStatus.UNREAD)
    )

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
    query = select(Notification).where(Notification.id == id, Notification.user_id == current_user.id)
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
    try:
        result = await db.execute(text("SELECT * FROM activity_logs ORDER BY timestamp DESC"))
        logs = result.mappings().all()  # Use `.mappings()` to fetch as dictionaries if needed
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching logs: {str(e)}")


@router.get("/secure-endpoint", dependencies=[Depends(get_role_validator(["admin", "editor"]))])
async def secure_endpoint():
    return {"message": "You have permission to access this resource."}


@router.get("/admin-only", dependencies=[Depends(get_role_validator(["admin"]))], status_code=status.HTTP_200_OK)
async def admin_only_endpoint():
    """
    This endpoint is restricted to admin users only.
    """
    return {"message": "This is restricted to admins only."}


@router.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    # Get inherited & raw permissions
    permissions = get_role_permissions(current_user.role.name)

    # Fetch all users
    result = await db.execute(select(User))
    all_users = result.scalars().all()

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "users": all_users, "current_user": current_user, "permissions": permissions},
    )


@router.get("/edit/{user_id}", response_class=HTMLResponse)
async def edit_user_form(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user_to_edit = result.scalar_one_or_none()
    if not user_to_edit:
        raise HTTPException(status_code=404, detail="User not found")

    return templates.TemplateResponse("edit_user_by_admin.html", {"request": request, "user_to_edit": user_to_edit})


@router.post("/user/edit/{user_id}")
async def edit_user_submit(
    user_id: int,
    username: str = Form(...),
    email: str = Form(...),
    db: AsyncSession = Depends(get_db),
    get_current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user_to_edit = result.scalar_one_or_none()
    if not user_to_edit:
        raise HTTPException(status_code=404, detail="User to edit not found")

    user_to_edit.username = username
    user_to_edit.email = email
    await db.commit()
    return RedirectResponse(url="/api/v1/users/admin/dashboard", status_code=302)
