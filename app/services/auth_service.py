from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth import hash_password, verify_password
from app.constants.roles import get_default_role_name
from app.models.user import Role, User


async def authenticate_user(email: str, password: str, db: AsyncSession):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user and verify_password(password, user.hashed_password):
        return user
    raise HTTPException(status_code=401, detail="Invalid credentials")


async def register_user(email: str, username: str, password: str, db: AsyncSession):
    result = await db.execute(select(User).where(User.email == email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Fetch the default role from database
    default_role_name = get_default_role_name()
    role_result = await db.execute(select(Role).where(Role.name == default_role_name))
    default_role = role_result.scalars().first()

    if not default_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Default role '{default_role_name}' not found in database",
        )

    new_user = User(email=email, username=username, hashed_password=hash_password(password), role_id=default_role.id)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
