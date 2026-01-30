from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import SignupRequest, LoginRequest
from app.security import hash_password, verify_password, create_access_token
from app.security import get_current_user
from app.schemas import SessionUser

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

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests

from app.database import get_db
from app.models import User
from app.security import create_access_token
from app.config import settings

@router.post("/google")
def google_auth(payload: dict, db: Session = Depends(get_db)):
    token = payload.get("id_token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing id_token")

    try:
        print("This is the Google Client: " + settings.GOOGLE_CLIENT_ID)
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    # ✅ THESE COME FROM GOOGLE, NOT REQUEST BODY
    email = idinfo.get("email")
    google_id = idinfo.get("sub")
    name = idinfo.get("name", "")

    if not email or not google_id:
        raise HTTPException(status_code=401, detail="Invalid Google token payload")

    user = db.query(User).filter(User.email == email).first()

    if user:
        if user.auth_provider != "google":
            raise HTTPException(
                status_code=400,
                detail="This account uses email & password login",
            )
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

    jwt_token = create_access_token(user.id)
    return {"access_token": jwt_token}


@router.get("/session", response_model=SessionUser)
def get_session(user: User = Depends(get_current_user)):
    return SessionUser(
        id=user.id,
        email=user.email,
        name=user.name,
        auth_provider=user.auth_provider,
    )
