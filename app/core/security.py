from jose import jwt
from datetime import datetime, timedelta
from app.core.config import settings

def create_jwt(subject: str) -> str:
    payload = {
        "sub": subject,
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    return jwt.encode(payload, settings.JWT_SECRET, settings.JWT_ALGORITHM)
