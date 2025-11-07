from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.location_routes import router as location_router
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="GatherUp AI - Location Service",
    description="Intelligent venue/location search service using Google Places API",
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
app.include_router(location_router, prefix="/api")

@app.get("/")
def root():
    return {
        "service": "GatherUp AI - Location Service",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "location-service"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("LOCATION_SERVICE_PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
