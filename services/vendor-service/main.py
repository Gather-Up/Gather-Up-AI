"""
Vendor Service - RAG-based vendor recommendation microservice
Handles vendor data management and intelligent recommendations using LLM
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.vendor_routes import router as vendor_router
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="GatherUp AI - Vendor Service",
    description="Intelligent vendor recommendation service using RAG pattern",
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
app.include_router(vendor_router, prefix="/api")

@app.get("/")
def root():
    return {
        "service": "GatherUp AI - Vendor Service",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "vendor-service"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("VENDOR_SERVICE_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
