import asyncio
# import os # No longer needed for path manipulation
# import sys # No longer needed for path manipulation
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# --- Import Project Settings and Metadata using relative paths ---
# Assumes env.py is in alembic/ and modules are in ../config/ and ../tokenomics/
try:
    from ..config.settings import settings # Import project settings
    from ..tokenomics.ledger import metadata as tokenomics_metadata # Import target metadata
except ImportError as e:
     # Provide more context if imports fail
     print(f"Error importing project modules in alembic/env.py: {e}")
     print("Ensure alembic commands are run from the project root directory containing 'Co-Lab'")
     print("Or adjust relative import paths if structure differs.")
     settings = None
     tokenomics_metadata = None


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the database URL from settings
# This overrides the (blank) value in alembic.ini
if settings and settings.LEDGER_DATABASE_URL:
     # Remove async driver part for alembic sync connection if needed
     sync_db_url = settings.LEDGER_DATABASE_URL
     if '+aiosqlite' in sync_db_url:
         sync_db_url = sync_db_url.replace('+aiosqlite','')
     elif '+asyncpg' in sync_db_url:
          sync_db_url = sync_db_url.replace('+asyncpg','')
     # Add other async driver replacements if necessary
     config.set_main_option("sqlalchemy.url", sync_db_url)
else:
     # Fallback or raise error if URL not set
     raise ValueError("LEDGER_DATABASE_URL not configured in settings or settings could not be imported.")


# Set the target metadata for 'autogenerate' support
target_metadata = tokenomics_metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    """
    if not target_metadata:
        print("Error: Target metadata not loaded. Cannot run offline migrations.")
        return
    # Use the URL set above
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # Pass target_metadata to context.configure
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode for async engines."""
    if not target_metadata:
        print("Error: Target metadata not loaded. Cannot run online migrations.")
        return

    # Use configuration from alembic.ini, including the URL set above
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # Pass target_metadata to run_sync's callable
        await connection.run_sync(do_run_migrations)

    # Dispose the engine explicitly for async
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Use asyncio.run to execute the async migration function
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()