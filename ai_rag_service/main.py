from fastapi import FastAPI
from routes import vendor_routes

app = FastAPI(title="Event Platform AI Service")

app.include_router(vendor_routes.router)

@app.get("/")
def root():
    return {"message": "AI Vendor Service is running"}
