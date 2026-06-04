from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["Pages"])

_FRONTEND_INDEX = Path(__file__).parent.parent.parent / "frontend" / "dist" / "index.html"


@router.get("/", tags=["Root"])
async def root():
    if _FRONTEND_INDEX.exists():
        return FileResponse(_FRONTEND_INDEX)
    return {"message": "Welcome to the CMS API"}
