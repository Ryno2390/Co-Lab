import databases
import sqlalchemy # Using SQLAlchemy core for query building
from ..config import settings
from contextlib import asynccontextmanager
from typing import Optional
import datetime # Import datetime for potential timestamp logic later

# --- Database Setup ---

DATABASE_URL = settings.LEDGER_DATABASE_URL
# Use connect_args for SQLite specific settings
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
database = databases.Database(DATABASE_URL, connect_args=connect_args)

# Define the table structure using SQLAlchemy Core (more flexible than ORM for simple cases)
metadata = sqlalchemy.MetaData()

user_balances = sqlalchemy.Table(
    "user_balances",
    metadata,
    sqlalchemy.Column("user_id", sqlalchemy.String, primary_key=True),
    # Using Numeric for potentially fractional tokens, adjust precision as needed
    # Defaulting balance to 0
    sqlalchemy.Column("balance", sqlalchemy.Numeric(18, 8), nullable=False, server_default=sqlalchemy.text("0.0")),
    sqlalchemy.Column("last_updated", sqlalchemy.DateTime, server_default=sqlalchemy.func.now(), onupdate=sqlalchemy.func.now())
)

# New table to track rewarded uploads for duplicate checking
rewarded_uploads = sqlalchemy.Table(
    "rewarded_uploads",
    metadata,
    sqlalchemy.Column("cid", sqlalchemy.String, primary_key=True), # IPFS Content ID
    sqlalchemy.Column("rewarded_at", sqlalchemy.DateTime, nullable=False, server_default=sqlalchemy.func.now()),
    # Optional: Add user_id who uploaded it, reward amount, etc. if needed later
    # sqlalchemy.Column("user_id", sqlalchemy.String, index=True),
    # sqlalchemy.Column("reward_amount", sqlalchemy.Numeric(18, 8))
)


# --- Database Connection Management ---

async def connect_db():
    """Connects to the database."""
    try:
        await database.connect()
        print("Ledger database connected.")
        # REMOVED: Schema creation is now handled by Alembic
    except Exception as e:
        print(f"Error connecting to ledger database: {e}")

async def disconnect_db():
    """Disconnects from the database."""
    try:
        if database.is_connected:
            await database.disconnect()
            print("Ledger database disconnected.")
        else:
            print("Ledger database already disconnected.")
    except Exception as e:
        print(f"Error disconnecting from ledger database: {e}")

@asynccontextmanager
async def db_session():
    """Provides a transactional database session."""
    if not database.is_connected:
        print("Warning: DB session requested but database not connected. Attempting connect.")
        await connect_db()
        if not database.is_connected:
             raise ConnectionError("Database connection failed within db_session context manager.")
    try:
        async with database.transaction():
            yield database
    except Exception:
        raise

# --- Ledger Operations ---

async def get_user_balance(user_id: str) -> Optional[float]:
    """Gets the current balance for a user."""
    async with db_session() as session:
        query = user_balances.select().where(user_balances.c.user_id == user_id)
        result = await session.fetch_one(query)
        return float(result["balance"]) if result else None

async def update_user_balance(user_id: str, amount_change: float) -> bool:
    """
    Updates a user's balance by a given amount (positive for credit, negative for debit).
    Uses a transaction for atomicity.
    """
    amount_str = f"{amount_change:.8f}"
    async with db_session() as session:
        select_query = user_balances.select().where(user_balances.c.user_id == user_id).with_for_update()
        result = await session.fetch_one(select_query)
        if not result:
            if amount_change > 0:
                print(f"User {user_id} not found, creating with balance {amount_change}")
                insert_query = user_balances.insert().values(user_id=user_id, balance=amount_str)
                await session.execute(insert_query)
                return True
            else:
                print(f"User {user_id} not found, cannot debit.")
                return False
        current_balance = float(result["balance"])
        new_balance = current_balance + amount_change
        if new_balance < 0:
            print(f"Insufficient balance for user {user_id} to debit {abs(amount_change)}")
            return False
        update_query = user_balances.update().where(user_balances.c.user_id == user_id).values(balance=f"{new_balance:.8f}")
        await session.execute(update_query)
        print(f"Updated balance for user {user_id} to {new_balance:.8f}")
        return True

# --- Rewarded Upload Tracking ---

async def add_rewarded_upload(cid: str):
    """
    Records a CID as having been rewarded using INSERT OR IGNORE (SQLite specific).
    If the CID already exists, the operation is ignored without error.
    """
    # Note: This uses SQLite specific syntax. For PostgreSQL use ON CONFLICT DO NOTHING.
    # SQLAlchemy Core can handle this with dialect-specific compilation, but raw SQL is simple here.
    raw_sql = sqlalchemy.text("INSERT OR IGNORE INTO rewarded_uploads (cid, rewarded_at) VALUES (:cid, :now)")
    async with db_session() as session:
        try:
            # Execute raw SQL with parameters
            await session.execute(query=raw_sql, values={"cid": cid, "now": datetime.datetime.now()})
            # We don't know for sure if a row was inserted or ignored without checking changes,
            # but for this purpose, just executing is often sufficient.
            print(f"Attempted to mark CID {cid} as rewarded in database (using INSERT OR IGNORE).")
        except Exception as e:
            print(f"Error adding rewarded upload for CID {cid}: {e}")
            # Decide if this should raise or just log

async def check_if_rewarded(cid: str) -> bool:
    """Checks if a CID has been previously rewarded."""
    # Note: Primary key lookup should be efficient.
    # TODO: Add time window logic if needed.
    async with db_session() as session:
        try:
            query = rewarded_uploads.select().where(rewarded_uploads.c.cid == cid)
            result = await session.fetch_one(query)
            return result is not None
        except Exception as e:
            print(f"Error checking rewarded status for CID {cid}: {e}")
            return False # Fail safe: assume not rewarded if check fails?