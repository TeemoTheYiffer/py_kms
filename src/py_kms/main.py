import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from py_kms.core.config import settings
from py_kms.core.security import create_api_key
from py_kms.core.database import init_db, get_db
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
        # Ensure app directory exists
        settings.APP_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Application directory ensured: {settings.APP_DIR}")
        
        # Initialize database and tables
        await init_db(settings.DB_PATH)
        logger.info(f"Database initialized at: {settings.DB_PATH}")
        
        # Get database connection
        db = await get_db()
        logger.info("Database connection established")
        
        # Check for existing API keys
        async with db.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM api_keys")
            result = await cur.fetchone()
            key_count = result[0] if result else 0
            
            if key_count == 0:
                # Generate default API key if none exists
                api_key, expires_at = await create_api_key()
                logger.info(f"Default API key initialized: {api_key}")
                logger.info(f"Expires at: {expires_at}")
            else:
                logger.info(f"Found {key_count} existing API keys")
                
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        db = await get_db()
        await db.disconnect()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")

# CORS middleware
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