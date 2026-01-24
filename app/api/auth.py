from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from app.core.security import create_jwt
from app.services.user_service import upsert_google_user
from app.core.config import settings
from fastapi import Depends
from app.core.auth import get_current_user

router = APIRouter()
oauth = OAuth()

router = APIRouter(prefix="/auth", tags=["auth"])

oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@router.get("/google/login")
async def google_login(request: Request):
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

from fastapi.responses import RedirectResponse

@router.get("/google/callback")
async def google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token["userinfo"]

    user = await upsert_google_user(userinfo)
    jwt_token = create_jwt(user.email)

    response = RedirectResponse(
        url="http://localhost:3000/auth/callback"
    )

    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        secure=False,      # True in production
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )

    return response

@router.get("/session")
async def session(user = Depends(get_current_user)):
    return {
        "authenticated": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "avatar": user.avatar,
        },
    }
