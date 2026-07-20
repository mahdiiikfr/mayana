import aiosqlite
import os
from pathlib import Path

from db.repositories.users import UserRepository
from db.repositories.vps import VPSRepository
from db.repositories.wallet import WalletRepository


class DatabaseManager:
    """
    DatabaseManager handles the lifecycle of SQLite asynchronous connection,
    initializes the tables, and instantiates the repositories.
    """
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.connection: aiosqlite.Connection | None = None

        # Repositories
        self.users: UserRepository | None = None
        self.vps: VPSRepository | None = None
        self.wallet: WalletRepository | None = None

    async def connect(self) -> None:
        """Establishes connection to SQLite database and instantiates repositories."""
        # Ensure directory for DB exists
        db_dir = Path(self.db_path).parent
        if db_dir:
            db_dir.mkdir(parents=True, exist_ok=True)

        self.connection = await aiosqlite.connect(self.db_path)
        # Enable Foreign Keys
        await self.connection.execute("PRAGMA foreign_keys = ON;")

        # Instantiate repositories passing the current connection
        self.users = UserRepository(self.connection)
        self.vps = VPSRepository(self.connection)
        self.wallet = WalletRepository(self.connection)

    async def disconnect(self) -> None:
        """Closes the SQLite database connection safely."""
        if self.connection:
            await self.connection.close()
            self.connection = None

    async def init_db(self) -> None:
        """Creates the initial database tables if they do not exist."""
        if not self.connection:
            raise RuntimeError("Database connection has not been established. Call connect() first.")

        # Table Creation SQL scripts
        users_table_sql = """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,          -- Telegram User ID
            username TEXT,                        -- Telegram Username
            full_name TEXT,                       -- Telegram Full Name
            language_code TEXT DEFAULT 'fa',      -- Language selection (e.g., 'fa', 'en')
            phone_number TEXT,                    -- Verified Phone Number
            is_verified INTEGER DEFAULT 0,        -- Verification status (0 = false, 1 = true)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        vps_table_sql = """
        CREATE TABLE IF NOT EXISTS vps (
            vps_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            openstack_uuid TEXT NOT NULL,         -- OpenStack instance UUID
            server_name TEXT NOT NULL,            -- Name of the VPS instance
            ip_address TEXT,                      -- Assigned IP address
            flavor TEXT,                          -- Flavor details
            status TEXT DEFAULT 'ACTIVE',         -- Current server status
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,                 -- Expiry / Billing check time
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        );
        """

        wallet_table_sql = """
        CREATE TABLE IF NOT EXISTS wallet (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            balance_after REAL DEFAULT 0.0,       -- Balance after the transaction
            transaction_type TEXT NOT NULL,       -- 'charge' or 'deduction'
            amount REAL NOT NULL,                 -- Transaction amount
            description TEXT,                     -- Transaction description / memo
            status TEXT DEFAULT 'COMPLETED',      -- 'PENDING', 'COMPLETED', 'FAILED'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
        );
        """

        # Execute scripts
        await self.connection.execute(users_table_sql)
        await self.connection.execute(vps_table_sql)
        await self.connection.execute(wallet_table_sql)
        await self.connection.commit()
