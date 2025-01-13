from cryptography.fernet import Fernet
from datetime import datetime
import json
import base64
from pathlib import Path
from typing import Dict, Union, Optional, List

from ..core.database import AsyncDatabaseManager, get_db

class AsyncKMS:
    def __init__(self):
        self._fernet: Optional[Fernet] = None
    
    async def initialize(self) -> None:
        """Initialize the KMS service"""
        await self._load_or_create_master_key()
    
    async def _load_or_create_master_key(self) -> None:
        """Load existing master key or create a new one"""
        db = await get_db()
        async with db.cursor() as cur:
            await cur.execute("SELECT key FROM master_key WHERE id = 1")
            result = await cur.fetchone()
            
            if not result:
                # Generate and store new master key
                master_key = Fernet.generate_key()
                async with db.transaction() as conn:
                    await conn.execute(
                        "INSERT INTO master_key (id, key) VALUES (1, ?)",
                        (master_key,)
                    )
                self._fernet = Fernet(master_key)
            else:
                self._fernet = Fernet(result[0])

    async def store_secret(
        self, 
        service_name: str, 
        secret_data: Union[str, bytes],
        metadata: Optional[Dict] = None
    ) -> None:
        """Store a secret with optional metadata"""
        if isinstance(secret_data, str):
            secret_data = secret_data.encode()
        
        secret_info = {
            "secret": base64.b64encode(secret_data).decode(),
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat()
        }
        
        encrypted_data = self._fernet.encrypt(json.dumps(secret_info).encode())
        
        db = await get_db()
        async with db.transaction() as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO secrets 
                (service_name, encrypted_data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (service_name, encrypted_data))

    async def get_secret(self, service_name: str) -> Dict:
        """Retrieve a secret and its metadata"""
        db = await get_db()
        async with db.cursor() as cur:
            await cur.execute("""
                SELECT encrypted_data 
                FROM secrets 
                WHERE service_name = ?
            """, (service_name,))
            result = await cur.fetchone()
            
            if not result:
                raise FileNotFoundError(f"No secret found for service: {service_name}")
            
            decrypted_data = self._fernet.decrypt(result[0])
            secret_info = json.loads(decrypted_data.decode())
            secret_info["secret"] = base64.b64decode(secret_info["secret"])
            
            return secret_info

    async def list_services(self) -> List[str]:
        """List all services that have stored secrets"""
        db = await get_db()
        async with db.cursor() as cur:
            await cur.execute("SELECT service_name FROM secrets ORDER BY service_name")
            results = await cur.fetchall()
            return [row[0] for row in results]

    async def remove_secret(self, service_name: str) -> None:
        """Remove a stored secret"""
        db = await get_db()
        async with db.transaction() as conn:
            cursor = await conn.execute("""
                DELETE FROM secrets 
                WHERE service_name = ?
            """, (service_name,))
            if cursor.rowcount == 0:
                raise FileNotFoundError(f"No secret found for service: {service_name}")

# Global KMS instance
_kms_instance: Optional[AsyncKMS] = None

async def get_kms() -> AsyncKMS:
    """Get the KMS service instance"""
    global _kms_instance
    if _kms_instance is None:
        _kms_instance = AsyncKMS()
        await _kms_instance.initialize()
    return _kms_instance