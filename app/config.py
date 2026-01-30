from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALEMBIC_DATABASE_URL: str | None = None  

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
