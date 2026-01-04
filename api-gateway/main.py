from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import httpx
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

app = FastAPI(
    title="GatherUp AI - API Gateway",
    description="Intelligent Event Planning Assistant - Main Entry Point",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs from environment variables
VENDOR_SERVICE_URL = os.getenv("VENDOR_SERVICE_URL")
LOCATION_SERVICE_URL = os.getenv("LOCATION_SERVICE_URL")
IMAGE_SERVICE_URL = os.getenv("IMAGE_SERVICE_URL", "http://localhost:8003")

# Request timeout
SERVICE_TIMEOUT = 30.0
IMAGE_SERVICE_TIMEOUT = 300.0


class EventPlanningRequest(BaseModel):
    """User's natural language prompt for event planning"""
    prompt: str = Field(..., description="Natural language description of the event needs")
    min_similarity: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum similarity threshold for vendors")
    max_results: Optional[int] = Field(3, ge=1, description="Maximum results for both vendors and locations")
    max_vendor_results: Optional[int] = Field(None, ge=1, le=5, description="Maximum vendor results (overrides max_results)")
    max_location_results: Optional[int] = Field(None, ge=1, description="Maximum location results (overrides max_results)")


class HealthStatus(BaseModel):
    status: str
    services: Dict[str, str]


@app.get("/", tags=["Health"])
def root():
    """Root endpoint"""
    return {
        "service": "GatherUp AI - API Gateway",
        "status": "running",
        "version": "1.0.0",
        "description": "Intelligent Event Planning Assistant"
    }


@app.get("/health", response_model=HealthStatus, tags=["Health"])
async def health_check():
    """
    Check health status of API Gateway and all microservices
    """
    services_status = {}
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Check Vendor Service
        try:
            response = await client.get(f"{VENDOR_SERVICE_URL}/health")
            services_status["vendor-service"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            services_status["vendor-service"] = f"unreachable: {str(e)}"
        
        # Check Location Service
        try:
            response = await client.get(f"{LOCATION_SERVICE_URL}/health")
            services_status["location-service"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            services_status["location-service"] = f"unreachable: {str(e)}"
        
        # Check Image Service
        try:
            response = await client.get(f"{IMAGE_SERVICE_URL}/health")
            services_status["image-service"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            services_status["image-service"] = f"unreachable: {str(e)}"
    
    all_healthy = all(status == "healthy" for status in services_status.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": services_status
    }


@app.post("/api/v1/plan-event", tags=["Event Planning"])
async def plan_event(request: EventPlanningRequest = Body(...)):
    """
    Main endpoint for event planning.
    Analyzes the user's prompt and returns recommendations from all services.
    
    Flow:
    1. Parse user's natural language prompt
    2. Query vendor-service for vendor recommendations (parallel)
    3. Query location-service for venue recommendations (parallel)
    4. Generate AI images for the event (parallel)
    5. Aggregate and return comprehensive results
    """
    
    if not request.prompt or not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    async with httpx.AsyncClient(timeout=SERVICE_TIMEOUT) as client:
        try:
            # Determine max_results for each service
            # If specific max_*_results is provided, use it; otherwise use general max_results
            vendor_max_results = request.max_vendor_results if request.max_vendor_results is not None else request.max_results
            location_max_results = request.max_location_results if request.max_location_results is not None else request.max_results
            
            # Prepare request payloads
            vendor_payload = {
                "user_prompt": request.prompt,
                "min_similarity": request.min_similarity,
                "max_results": vendor_max_results
            }
            
            location_payload = {
                "query": request.prompt,
                "max_results": location_max_results
            }
            
            # Call all services in parallel for efficiency
            vendor_task = client.post(
                f"{VENDOR_SERVICE_URL}/api/vendors/recommend",
                json=vendor_payload
            )
            
            location_task = client.post(
                f"{LOCATION_SERVICE_URL}/api/locations/search",
                json=location_payload
            )
            
            # Get AI-enhanced prompt for image generation (no actual image generation)
            prompt_task = client.post(
                f"{IMAGE_SERVICE_URL}/api/images/enhance-prompt",
                params={"prompt": request.prompt},
                timeout=30.0
            )
            
            # Wait for all responses
            vendor_response, location_response, prompt_response = await asyncio.gather(
                vendor_task,
                location_task,
                prompt_task,
                return_exceptions=True
            )
            
            # Process vendor service response
            vendor_data = {}
            if isinstance(vendor_response, Exception):
                vendor_data = {
                    "status": "error",
                    "message": f"Vendor service error: {str(vendor_response)}",
                    "vendors": []
                }
            elif vendor_response.status_code == 200:
                vendor_data = vendor_response.json()
            else:
                vendor_data = {
                    "status": "error",
                    "message": f"Vendor service returned status {vendor_response.status_code}",
                    "vendors": []
                }
            
            # Process location service response
            location_data = {}
            if isinstance(location_response, Exception):
                location_data = {
                    "status": "error",
                    "message": f"Location service error: {str(location_response)}",
                    "locations": []
                }
            elif location_response.status_code == 200:
                location_data = location_response.json()
            else:
                location_data = {
                    "status": "error",
                    "message": f"Location service returned status {location_response.status_code}",
                    "locations": []
                }
            
            # Process enhanced prompt response
            image_prompt_data = {}
            if isinstance(prompt_response, Exception):
                image_prompt_data = {
                    "status": "error",
                    "message": f"Prompt enhancement error: {str(prompt_response)}"
                }
            elif prompt_response.status_code == 200:
                image_prompt_data = prompt_response.json()
            else:
                image_prompt_data = {
                    "status": "error",
                    "message": f"Prompt service returned status {prompt_response.status_code}"
                }
            
            # Aggregate results
            return {
                "status": "success",
                "user_prompt": request.prompt,
                "recommendations": {
                    "vendors": vendor_data,
                    "locations": location_data
                },
                "image_generation_prompt": image_prompt_data.get("enhanced_prompt", request.prompt),
                "summary": generate_summary(vendor_data, location_data)
            }
            
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Request timeout - services took too long to respond"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )


@app.post("/api/v1/vendors/recommend", tags=["Vendors"])
async def recommend_vendors_only(request: EventPlanningRequest = Body(...)):
    """
    Direct vendor recommendations endpoint (bypasses aggregation)
    """
    async with httpx.AsyncClient(timeout=SERVICE_TIMEOUT) as client:
        try:
            payload = {
                "user_prompt": request.prompt,
                "min_similarity": request.min_similarity,
                "max_results": request.max_results
            }
            
            response = await client.post(
                f"{VENDOR_SERVICE_URL}/api/vendors/recommend",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Vendor service error: {response.text}"
                )
                
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Vendor service timeout")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Cannot reach vendor service: {str(e)}")


@app.post("/api/v1/locations/search", tags=["Locations"])
async def search_locations_only(
    query: str = Body(..., embed=True),
    max_results: Optional[int] = Body(3, embed=True)
):
    """
    Direct location search endpoint (bypasses aggregation)
    """
    async with httpx.AsyncClient(timeout=SERVICE_TIMEOUT) as client:
        try:
            payload = {
                "query": query,
                "max_results": max_results
            }
            
            response = await client.post(
                f"{LOCATION_SERVICE_URL}/api/locations/search",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Location service error: {response.text}"
                )
                
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Location service timeout")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Cannot reach location service: {str(e)}")


def generate_summary(vendor_data: Dict, location_data: Dict) -> str:
    """Generate a human-readable summary of the recommendations"""
    vendors_found = vendor_data.get("vendors_found", 0)
    locations_found = location_data.get("locations_found", 0)
    
    summary_parts = []
    
    if vendors_found > 0:
        summary_parts.append(f"Found {vendors_found} suitable vendor(s)")
    
    if locations_found > 0:
        summary_parts.append(f"Found {locations_found} venue(s)")
    
    if not summary_parts:
        return "No recommendations found. Please try refining your search criteria."
    
    return " and ".join(summary_parts) + " for your event."


# ========== IMAGE GENERATION ENDPOINTS ==========

class ImageGenerationRequest(BaseModel):
    """Image generation request schema"""
    prompt: str = Field(..., description="Description of the image to generate")
    num_images: int = Field(default=1, ge=1, le=3, description="Number of images (1-3)")
    negative_prompt: Optional[str] = None
    width: int = Field(default=1024, ge=512, le=2048)
    height: int = Field(default=1024, ge=512, le=2048)
    steps: int = Field(default=30, ge=1, le=150)
    cfg_scale: float = Field(default=7.0, ge=1.0, le=30.0)
    sampler_name: str = Field(default="dpmpp_2m")
    scheduler: str = Field(default="karras")
    seed: Optional[int] = None
    denoise: float = Field(default=1.0, ge=0.0, le=1.0)
    use_refiner: bool = Field(default=True, description="Use SDXL Refiner for enhanced quality (True = Base+Refiner, False = Base only)")


@app.post("/api/v1/images/generate", tags=["Images"])
async def generate_images(request: ImageGenerationRequest = Body(...)):
    """
    Generate images using SDXL via ComfyUI (non-streaming)
    Returns complete result after generation
    """
    async with httpx.AsyncClient(timeout=IMAGE_SERVICE_TIMEOUT) as client:
        try:
            response = await client.post(
                f"{IMAGE_SERVICE_URL}/api/images/generate",
                json=request.model_dump()
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Image service error: {response.text}"
                )
        
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="Image generation timeout - please try with fewer steps or smaller images"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Cannot reach image service: {str(e)}"
            )


@app.post("/api/v1/images/generate/stream", tags=["Images"])
async def generate_images_stream(request: ImageGenerationRequest = Body(...)):
    """
    Generate images with real-time streaming progress (SSE)
    Perfect for frontend integration with live updates
    """
    async def stream_from_image_service():
        try:
            async with httpx.AsyncClient(timeout=IMAGE_SERVICE_TIMEOUT) as client:
                async with client.stream(
                    "POST",
                    f"{IMAGE_SERVICE_URL}/api/images/generate/stream",
                    json=request.model_dump()
                ) as response:
                    if response.status_code != 200:
                        yield f"data: {{\"status\": \"error\", \"message\": \"Image service error: {response.status_code}\"}}\n\n"
                        return
                    
                    async for chunk in response.aiter_text():
                        yield chunk
        
        except Exception as e:
            yield f"data: {{\"status\": \"error\", \"message\": \"Stream error: {str(e)}\"}}\n\n"
    
    return StreamingResponse(
        stream_from_image_service(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/v1/images/enhance-prompt", tags=["Images"])
async def enhance_image_prompt(prompt: str = Body(..., embed=True)):
    """
    Enhance a prompt for better image generation using Llama 3.2
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{IMAGE_SERVICE_URL}/api/images/enhance-prompt",
                params={"prompt": prompt}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Prompt enhancement error: {response.text}"
                )
        
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Prompt enhancement timeout")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Cannot reach image service: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("GATEWAY_PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
