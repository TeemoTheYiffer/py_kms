from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from ...core.security import verify_api_key, create_api_key 
from ...services.kms import get_kms, AsyncKMS
from ...core.config import settings
from ..models.secret import SecretsResponse, ServiceList, APIKeyResponse
import json

router = APIRouter()

@router.post(
    "/{service_name}",
    response_model=SecretsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store a new secret"
)
async def store_secret(
    service_name: str,
    secret_data: str = Form(..., description="Secret content"),
    metadata: str = Form(default="{}", description="Optional JSON metadata"),
    kms: AsyncKMS = Depends(get_kms)
) -> SecretsResponse:
    """Store a secret for a service"""
    try:
        # Parse metadata if provided
        meta_dict = json.loads(metadata)
        
        # Add timestamp to metadata
        meta_dict["stored_at"] = str(datetime.now())
        
        await kms.store_secret(
            service_name=service_name,
            secret_data=secret_data,
            metadata=meta_dict
        )
        
        return SecretsResponse(
            service_name=service_name,
            secret=secret_data,
            metadata=meta_dict,
            created_at=meta_dict["stored_at"]
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid metadata JSON format"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get(
    "/{service_name}",
    response_model=SecretsResponse,
    summary="Retrieve a secret"
)
async def get_secret(
    service_name: str,
    kms: AsyncKMS = Depends(get_kms),
    api_key: str = Depends(verify_api_key)
) -> SecretsResponse:
    """Retrieve a secret and its metadata"""
    try:
        secret_info = await kms.get_secret(service_name)
        return SecretsResponse(
            service_name=service_name,
            secret=secret_info["secret"].decode(),
            metadata=secret_info["metadata"],
            created_at=secret_info["metadata"]["stored_at"]
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No secret found for service: {service_name}"
        )

@router.get(
    "/",
    response_model=ServiceList,
    summary="List all secret services"
)
async def list_secrets(
    kms: AsyncKMS = Depends(get_kms),
    api_key: str = Depends(verify_api_key)
) -> ServiceList:
    """List all services that have stored secrets"""
    services = await kms.list_services()
    return ServiceList(services=services, total_count=len(services))

@router.delete(
    "/{service_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a secret"
)
async def delete_secret(
    service_name: str,
    api_key: str = Depends(verify_api_key),
    kms: AsyncKMS = Depends(get_kms)
) -> None:
    """Delete a stored secret"""
    try:
        await kms.remove_secret(service_name)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No secret found for service: {service_name}"
        )

@router.post(
    "/admin/api-keys/{key_name}",
    response_model=APIKeyResponse,
    summary="Create a new API key",
)
async def create_new_api_key(
    key_name: str,
    ttl_days: int = Query(default=30, gt=0, le=365),
    current_api_key: str = Depends(verify_api_key)
) -> APIKeyResponse:
    """Create a new API key with a given name"""
    new_key, created_at = await create_api_key(key_name, ttl_days)
    if not new_key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"API key with name '{key_name}' already exists"
        )
    
    return APIKeyResponse(
        key_name=key_name,
        api_key=new_key,
        created_at=str(datetime.now())
    )