import asyncio
from app.db.session import engine
from app.db.base import Base
from app.db import models  # MUST import

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("TABLES CREATED")

asyncio.run(main())
