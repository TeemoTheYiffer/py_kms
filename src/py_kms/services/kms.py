from cryptography.fernet import Fernet
from datetime import datetime
import json
import base64
import sqlite3
from pathlib import Path
from typing import Dict, Union, Optional
from ..core.database import get_db_connection

class KMS:
    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """
        Initialize the KMS with a SQLite database.
        
        Args:
            db_path: Path to SQLite database. If None, uses an OS-appropriate default location
        """
        if db_path is None:
            app_dir = Path.home() / ".py_kms"
            app_dir.mkdir(exist_ok=True)
            db_path = app_dir / "kms.db"
        
        self.db_path = Path(db_path)
        self._load_or_create_master_key()

    def _load_or_create_master_key(self) -> None:
        """Load existing master key or create a new one."""
        with get_db_connection(self.db_path) as conn:
            master_key = conn.execute("SELECT key FROM master_key WHERE id = 1").fetchone()
            
            if not master_key:
                # Generate and store new master key
                master_key = Fernet.generate_key()
                conn.execute("INSERT INTO master_key (id, key) VALUES (1, ?)", (master_key,))
                self._fernet = Fernet(master_key)
            else:
                self._fernet = Fernet(master_key[0])

    def store_secret(
        self, 
        service_name: str, 
        secret_data: Union[str, bytes],
        metadata: Optional[Dict] = None
    ) -> None:
        """Store a secret with optional metadata."""
        if isinstance(secret_data, str):
            secret_data = secret_data.encode()
        
        secret_info = {
            "secret": base64.b64encode(secret_data).decode(),
            "metadata": metadata or {},
            "created_at": str(datetime.now().isoformat())
        }
        
        encrypted_data = self._fernet.encrypt(json.dumps(secret_info).encode())
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO secrets (service_name, encrypted_data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (service_name, encrypted_data))

    def get_secret(self, service_name: str) -> Dict:
        """Retrieve a secret and its metadata."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT encrypted_data 
                FROM secrets 
                WHERE service_name = ?
            """, (service_name,)).fetchone()
            
            if not result:
                raise FileNotFoundError(f"No secret found for service: {service_name}")
            
            decrypted_data = self._fernet.decrypt(result[0])
            secret_info = json.loads(decrypted_data.decode())
            secret_info["secret"] = base64.b64decode(secret_info["secret"])
            
            return secret_info

    def list_services(self) -> list[str]:
        """List all services that have stored secrets."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT service_name FROM secrets ORDER BY service_name")
            return [row[0] for row in cursor.fetchall()]

    def remove_secret(self, service_name: str) -> None:
        """Remove a stored secret."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM secrets 
                WHERE service_name = ?
            """, (service_name,))
            
            if cursor.rowcount == 0:
                raise FileNotFoundError(f"No secret found for service: {service_name}")

    def get_secret_info(self, service_name: str) -> Dict:
        """Get secret metadata without the actual secret content."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT encrypted_data, created_at, updated_at 
                FROM secrets 
                WHERE service_name = ?
            """, (service_name,)).fetchone()
            
            if not result:
                raise FileNotFoundError(f"No secret found for service: {service_name}")
            
            decrypted_data = self._fernet.decrypt(result[0])
            secret_info = json.loads(decrypted_data.decode())
            
            return {
                "service_name": service_name,
                "metadata": secret_info["metadata"],
                "created_at": result[1],
                "updated_at": result[2]
            }