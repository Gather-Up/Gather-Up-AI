from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.image_routes import router as image_router
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="GatherUp AI - Image Service",
    description="Intelligent image generation service using Stable Diffusion XL via ComfyUI",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(image_router, prefix="/api")

@app.get("/")
def root():
    return {
        "service": "GatherUp AI - Image Service",
        "status": "running",
        "version": "1.0.0",
        "model": "Stable Diffusion XL via ComfyUI",
        "capabilities": [
            "Text-to-image generation",
            "Prompt enhancement with Llama 3.2 3B",
            "Real-time streaming progress",
            "Batch generation (up to 3 images)",
            "Full SDXL customization support"
        ]
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "image-service"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("IMAGE_SERVICE_PORT", "8003"))
    uvicorn.run(app, host="0.0.0.0", port=port)
