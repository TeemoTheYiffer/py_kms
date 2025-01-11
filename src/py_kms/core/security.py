from datetime import datetime, timedelta
import secrets
from typing import Optional, Tuple
import sqlite3
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from py_kms.core.config import settings
from .database import get_db_connection

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)

def create_api_key(key_name: str = "default", ttl_days: int = 30) -> Tuple[str, datetime]:
    """Create a new API key with expiration"""
    with sqlite3.connect(settings.DB_PATH) as conn:
        # Only check existing if it's not the default key
        if key_name != "default":
            existing = conn.execute(
                "SELECT 1 FROM api_keys WHERE key_id = ?",
                (key_name,)
            ).fetchone()
            if existing:
                return None, None
            
        api_key = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=ttl_days)
        
        conn.execute(
            "INSERT OR REPLACE INTO api_keys (key_id, api_key, expires_at) VALUES (?, ?, ?)",
            (key_name, api_key, expires_at)
        )
        conn.commit()
        
        return api_key, expires_at

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Verify the API key is valid and not expired"""
    with get_db_connection(settings.DB_PATH) as conn:
        result = conn.execute(
            """
            SELECT expires_at, is_active 
            FROM api_keys 
            WHERE api_key = ?
            """, 
            (api_key,)
        ).fetchone()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API key"
            )
        
        expires_at, is_active = result
        
        if not is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key has been deactivated"
            )
            
        if datetime.fromisoformat(expires_at) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key has expired"
            )
            
    return api_key