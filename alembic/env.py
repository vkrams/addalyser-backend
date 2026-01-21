from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base
from app.db import models  # noqa: F401

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
    """Run migrations in ONLINE mode (SYNC, Windows-safe)."""

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
