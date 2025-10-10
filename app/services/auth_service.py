from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.models.user import User
from app.auth import verify_password, hash_password

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
    
    new_user = User(
        email=email,
        username=username,
        hashed_password = hash_password(password),
        role_id=2
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user