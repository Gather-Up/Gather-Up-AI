"""
Image Service Main Application  
FastAPI microservice for AI-powered image generation with ComfyUI integration
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from routes.image_routes import router as image_router, init_services
from services.comfyui_client import ComfyUIClient
from services.ollama_service import OllamaService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
comfyui_client: ComfyUIClient = None
ollama_service: OllamaService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown"""
    global comfyui_client, ollama_service
    
    # Startup
    logger.info("Starting Image Service...")
    
    # Initialize ComfyUI client
    comfyui_url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8000")
    comfyui_timeout = int(os.getenv("COMFYUI_TIMEOUT", "300"))
    comfyui_client = ComfyUIClient(comfyui_url, comfyui_timeout)
    
    # Initialize Ollama service (cloud-based, same as vendor service)
    ollama_service = OllamaService()
    
    # Initialize Cloudinary config
    cloudinary_config = {
        "cloud_name": os.getenv("CLOUDINARY_CLOUD_NAME"),
        "api_key": os.getenv("CLOUDINARY_API_KEY"),
        "api_secret": os.getenv("CLOUDINARY_API_SECRET")
    }
    
    # Initialize routes with services
    init_services(comfyui_client, ollama_service, cloudinary_config)
    
    # Check connections
    comfyui_connected = await comfyui_client.check_connection()
    ollama_connected = await ollama_service.check_connection()
    
    logger.info(f"ComfyUI Connection: {'✓ Connected' if comfyui_connected else '✗ Failed'}")
    logger.info(f"Cloud LLM Connection: {'✓ Connected' if ollama_connected else '✗ Failed (will use fallback)'}")
    
    if not comfyui_connected:
        logger.warning(f"Cannot connect to ComfyUI at {comfyui_url}")
        logger.warning("Make sure ComfyUI is running before generating images")
    
    if not ollama_connected:
        logger.warning(f"Cannot connect to cloud-based LLM")
        logger.warning("Prompt enhancement will use fallback mode")
    
    logger.info("Image Service started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Image Service...")


# Create FastAPI app
app = FastAPI(
    title="GatherUp Image Service",
    description="AI-Powered Image Generation Service using ComfyUI and Ollama",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(image_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "GatherUp Image Service",
        "status": "running",
        "version": "1.0.0",
        "description": "AI-Powered Image Generation using ComfyUI and Ollama",
        "endpoints": {
            "generate": "/api/images/generate",
            "enhance_prompt": "/api/images/enhance-prompt",
            "batch_generate": "/api/images/generate-batch",
            "health": "/api/images/health",
            "models": "/api/images/models",
            "config": "/api/images/config",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health():
    """Simple health check"""
    return {"status": "healthy", "service": "image-service"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "details": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("IMAGE_SERVICE_HOST", "0.0.0.0")
    port = int(os.getenv("IMAGE_SERVICE_PORT", "8003"))
    
    logger.info(f"Starting Image Service on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
