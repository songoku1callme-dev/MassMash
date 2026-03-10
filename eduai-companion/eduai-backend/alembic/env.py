"""Alembic env.py — Lumnos Companion database migrations.

Reads DATABASE_URL from the environment so that the same alembic.ini
works for local development (SQLite) and production (PostgreSQL on Fly.io).
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to alembic.ini values
# ---------------------------------------------------------------------------
config = context.config

# Override sqlalchemy.url with DATABASE_URL env var when available.
# This allows Fly.io / Docker / CI to inject the real connection string
# without touching alembic.ini.
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Python logging from config file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Model MetaData for autogenerate support
# ---------------------------------------------------------------------------
# Lumnos uses raw SQL via sqlite3 / psycopg, so there is no SQLAlchemy
# declarative Base.  We set target_metadata = None and manage migrations
# manually via `alembic revision -m "..."` (not --autogenerate).
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL so that calls to
    context.execute() emit SQL to the script output without
    requiring a live database connection.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
