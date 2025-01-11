from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseSettings, root_validator

class Settings(BaseSettings):
    """Core settings for KMS"""
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Simple KMS"
    
    # Security - Essential for KMS
    API_KEYS: Dict[str, str] = {}
    DEFAULT_API_KEY: Optional[str] = None
    
    # Database and Storage
    APP_DIR: Path = Path.home() / ".py_kms"
    DB_PATH: Path = APP_DIR / "kms.db"
    
    # Basic logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Path = APP_DIR / "kms.log"

    @root_validator
    def validate_paths(cls, values: dict) -> dict:
        """Ensure app directory exists"""
        app_dir = values.get("APP_DIR")
        if app_dir:
            app_dir.mkdir(parents=True, exist_ok=True)
        return values

    class Config:
        case_sensitive = True
        env_prefix = "KMS_"

# Initialize settings
settings = Settings()