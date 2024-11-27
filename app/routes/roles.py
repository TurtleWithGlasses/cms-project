from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import Role
from app.database import get_db
from typing import List

router = APIRouter()

@router.get("/roles", response_model=List[str], tags=["Roles"])
async def get_roles(db: AsyncSession = Depends(get_db)):
    """
    Fetch all available roles from the database.
    """
    try:
        # Query to get all roles
        result = await db.execute(select(Role.name))
        roles = result.scalars().all()
        return roles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching roles: {str(e)}")
