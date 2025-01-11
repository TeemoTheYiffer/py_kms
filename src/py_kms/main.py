import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from py_kms.core.config import settings
from py_kms.core.security import create_api_key
from py_kms.core.database import init_db
from py_kms.api.routes import secrets

# Setup logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Initializing KMS service")
    try:
        # Initialize all database tables
        init_db(settings.DB_PATH)
        
        # Generate default API key if none exists
        api_key, expires_at = create_api_key()
        logger.info(f"Default API key initialized: {api_key}")
        logger.info(f"Expires at: {expires_at}")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize API routes
app.include_router(
    secrets.router,
    prefix=f"{settings.API_V1_STR}/secrets",
    tags=["secrets"]
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )