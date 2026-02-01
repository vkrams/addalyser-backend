from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base 
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    auth_provider = Column(String, nullable=False)
    google_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())