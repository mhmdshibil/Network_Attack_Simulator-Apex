"""
Alembic async environment for Apex Argus.

Reads DATABASE_URL from the environment (same URL the app uses) and runs
migrations against the async engine (asyncpg / aiosqlite). Autogenerate targets
Base.metadata from backend.app.core.database.
"""
import asyncio
import os
import pathlib
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Make the project importable when alembic runs from the repo root.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from backend.app.core.database import Base, DATABASE_URL  # noqa: E402
import backend.app.models  # noqa: E402,F401 — register all tables on Base.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the runtime database URL.
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", DATABASE_URL))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
