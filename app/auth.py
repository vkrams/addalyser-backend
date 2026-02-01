from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import User
from app.schemas import SignupRequest, LoginRequest
from app.security import hash_password, verify_password, create_access_token
from app.security import get_current_user
from app.schemas import SessionUser
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests

from app.database import get_db
from app.config import settings
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests
from jose import JWTError

from app.database import get_db
from app.models import User
from app.security import create_access_token
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup")
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(400, "Account already exists")

    user = User(
        email=data.email,
        name=data.name,
        password_hash=hash_password(data.password),
        auth_provider="local"
    )
    db.add(user)
    db.commit()

    return {"message": "Signup successful"}

@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(404, "Account not found")

    if user.auth_provider != "local":
        raise HTTPException(400, "Use Google Sign-In")

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    token = create_access_token(user.id)
    return {"access_token": token}

@router.get("/session", response_model=SessionUser)
def get_session(user: User = Depends(get_current_user)):
    return SessionUser(
        id=user.id,
        email=user.email,
        name=user.name,
        auth_provider=user.auth_provider,
    )

class GoogleLoginPayload(BaseModel):
    id_token: str


@router.post("/google/login")
def google_auth(
    payload: GoogleLoginPayload,
    db: Session = Depends(get_db),
):
    # 1️⃣ Verify Google ID token
    try:
        idinfo = id_token.verify_oauth2_token(
            payload.id_token,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    # Extra safety (recommended)
    if idinfo["iss"] not in [
        "accounts.google.com",
        "https://accounts.google.com",
    ]:
        raise HTTPException(status_code=401, detail="Invalid token issuer")

    email = idinfo.get("email")
    google_id = idinfo.get("sub")
    name = idinfo.get("name", "")

    if not email or not google_id:
        raise HTTPException(status_code=401, detail="Invalid Google token payload")

    # 2️⃣ Check user
    user = db.query(User).filter(User.email == email).first()

    # 3️⃣ EXISTING USER (Scenario 2)
    if user:
        if user.auth_provider != "google":
            raise HTTPException(
                status_code=400,
                detail="This account uses email/password login",
            )

    # 4️⃣ NEW USER (Scenario 1)
    else:
        user = User(
            email=email,
            name=name,
            auth_provider="google",
            google_id=google_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 5️⃣ Create JWT
    access_token = create_access_token(
        {"sub": str(user.id)}
    )

    return {
        "access_token": access_token,
        "is_new_user": user.google_id == google_id,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
        },
    }
