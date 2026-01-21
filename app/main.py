from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.users import router as users_router  # ✅ add

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET,
)

app.include_router(auth_router)
app.include_router(users_router)  # ✅ add
