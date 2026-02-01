from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from app.database import engine

from app.config import settings
from app.database import Base
import app.models

# Alembic Config
config = context.config

# Logging
fileConfig(config.config_file_name)

# Metadata
target_metadata = Base.metadata

# Use SYNC database URL for Alembic
config.set_main_option(
    "sqlalchemy.url",
    settings.ALEMBIC_DATABASE_URL,
)


def run_migrations_online():
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
