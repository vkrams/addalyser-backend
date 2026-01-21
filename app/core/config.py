from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    SESSION_SECRET: str
    ALEMBIC_DATABASE_URL: str
    class Config:
        env_file = ".env"

settings = Settings()
