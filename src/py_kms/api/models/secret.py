from typing import Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class SecretsData(BaseModel):
    """Model for secrets storage requests"""
    secrets_content: str = Field(..., description="Secret content")
    metadata: Optional[Dict] = Field(
        default_factory=dict,
        description="Optional metadata about the secret"
    )

class SecretsResponse(BaseModel):
    """Model for secrets retrieval responses"""
    service_name: str
    secret: str
    metadata: Dict
    created_at: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "service_name": "web_service",
                "secret": "-----BEGIN OPENSSH PRIVATE KEY-----\n...",
                "metadata": {"environment": "production", "owner": "devops"},
                "created_at": "2024-01-10T12:00:00Z"
            }
        }

class ServiceList(BaseModel):
    """Model for listing services that have stored secrets"""
    services: list[str]
    total_count: int

    class Config:
        schema_extra = {
            "example": {
                "services": ["web_api", "database", "monitoring"],
                "total_count": 3
            }
        }

class APIKeyResponse(BaseModel):
    """Model for API key creation response"""
    key_name: str
    api_key: str
    created_at: datetime