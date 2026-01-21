from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.db.models import User

router = APIRouter()

@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar": user.avatar,
        "provider": user.provider,
        "created_at": user.created_at,
    }
