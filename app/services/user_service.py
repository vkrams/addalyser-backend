from uuid import uuid4
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import User

async def upsert_google_user(profile: dict):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.email == profile["email"])
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                id=str(uuid4()),
                email=profile["email"],
                name=profile.get("name"),
                avatar=profile.get("picture"),
                provider="google",
                provider_id=profile["sub"],
            )
            db.add(user)

        await db.commit()
        return user
