from typing import AsyncGenerator, Optional
import aiosqlite
from contextlib import asynccontextmanager
from pathlib import Path

class AsyncDatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None
        
    async def connect(self) -> None:
        """Initialize the database connection"""
        if not self._db:
            self._db = await aiosqlite.connect(str(self.db_path))
            await self._db.execute("PRAGMA journal_mode = WAL")
            await self._db.execute("PRAGMA foreign_keys = ON")
            self._db.row_factory = aiosqlite.Row
    
    async def disconnect(self) -> None:
        """Close the database connection"""
        if self._db:
            await self._db.close()
            self._db = None

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Context manager for database transactions"""
        if not self._db:
            await self.connect()
            
        async with self._db.cursor() as cur:
            await cur.execute("BEGIN")
            try:
                yield self._db
                await self._db.commit()
            except:
                await self._db.rollback()
                raise

    @asynccontextmanager
    async def cursor(self) -> AsyncGenerator[aiosqlite.Cursor, None]:
        """Context manager for database cursors"""
        if not self._db:
            await self.connect()
            
        async with self._db.cursor() as cur:
            yield cur

async def init_db(db_path: Path) -> None:
    """Initialize all database tables"""
    async with aiosqlite.connect(str(db_path)) as db:
        await db.execute("PRAGMA journal_mode = WAL")
        await db.execute("PRAGMA foreign_keys = ON")
        
        # Create tables
        await db.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id TEXT PRIMARY KEY,
                api_key TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS secrets (
                service_name TEXT PRIMARY KEY,
                encrypted_data BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS master_key (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                key BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.commit()

# Global database instance
_db_manager: Optional[AsyncDatabaseManager] = None

async def get_db() -> AsyncDatabaseManager:
    """Get the database manager instance"""
    global _db_manager
    if _db_manager is None:
        from py_kms.core.config import settings
        _db_manager = AsyncDatabaseManager(settings.DB_PATH)
        await _db_manager.connect()
    return _db_manager