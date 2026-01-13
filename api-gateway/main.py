from fastapi import FastAPI, HTTPException, Body, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
import httpx
import os
from dotenv import load_dotenv
import asyncio
import logging
import re
from datetime import datetime, timedelta
import html
import json
import base64
from database import (
    EmailTemplateModel, 
    GeneratedEventModel, 
    verify_connection, 
    EventModel,
    TasksModel,
    GeneratedMediaHistoryModel
)
from cloudinary_service import upload_base64_image

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Validate critical environment variables
required_env_vars = ['VENDOR_SERVICE_URL', 'LOCATION_SERVICE_URL']
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing_vars)}")

app = FastAPI(
    title="GatherUp AI - API Gateway",
    description="Intelligent Event Planning Assistant - Main Entry Point",
    version="1.0.0"
)

# Allowed origins from environment or default
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000"
).split(",")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    max_age=3600,
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    # Skip security headers for OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        response = await call_next(request)
        return response
    
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Service URLs from environment variables
VENDOR_SERVICE_URL = os.getenv("VENDOR_SERVICE_URL")
LOCATION_SERVICE_URL = os.getenv("LOCATION_SERVICE_URL")
IMAGE_SERVICE_URL = os.getenv("IMAGE_SERVICE_URL", "http://localhost:8003")

# Request timeout
SERVICE_TIMEOUT = 30.0
IMAGE_SERVICE_TIMEOUT = 300.0

# Input validation constants
MAX_PROMPT_LENGTH = 1000
MIN_PROMPT_LENGTH = 3
MAX_VENDOR_RESULTS = 10
MAX_LOCATION_RESULTS = 20

# Suspicious patterns for prompt injection detection
SUSPICIOUS_PATTERNS = [
    r'<script[^>]*>',
    r'javascript:',
    r'on\w+\s*=',
    r'eval\s*\(',
    r'exec\s*\(',
]

def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent injection attacks"""
    if not text:
        return ""
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Escape HTML entities
    text = html.escape(text)
    
    # Remove excessive whitespace
    text = ' '.join(text.split())
    
    # Check for suspicious patterns
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"Suspicious pattern detected in input: {pattern}")
            raise HTTPException(
                status_code=400,
                detail="Invalid input detected. Please remove special characters or code."
            )
    
    return text.strip()

def validate_prompt_length(prompt: str) -> str:
    """Validate prompt length"""
    if len(prompt) < MIN_PROMPT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Prompt is too short. Minimum length is {MIN_PROMPT_LENGTH} characters."
        )
    
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Prompt is too long. Maximum length is {MAX_PROMPT_LENGTH} characters."
        )
    
    return prompt


class EventPlanningRequest(BaseModel):
    """User's natural language prompt for event planning"""
    prompt: str = Field(
        ...,
        min_length=MIN_PROMPT_LENGTH,
        max_length=MAX_PROMPT_LENGTH,
        description="Natural language description of the event needs"
    )
    min_similarity: Optional[float] = Field(
        0.6,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold for vendors"
    )
    max_results: Optional[int] = Field(
        3,
        ge=1,
        le=MAX_VENDOR_RESULTS,
        description="Maximum results for both vendors and locations"
    )
    max_vendor_results: Optional[int] = Field(
        None,
        ge=1,
        le=MAX_VENDOR_RESULTS,
        description="Maximum vendor results (overrides max_results)"
    )
    max_location_results: Optional[int] = Field(
        None,
        ge=1,
        le=MAX_LOCATION_RESULTS,
        description="Maximum location results (overrides max_results)"
    )
    
    @field_validator('prompt')
    @classmethod
    def validate_and_sanitize_prompt(cls, v):
        """Validate and sanitize prompt"""
        if not v or not v.strip():
            raise ValueError("Prompt cannot be empty")
        return sanitize_input(v)
    
    @field_validator('max_vendor_results', 'max_location_results')
    @classmethod
    def validate_max_results(cls, v, info):
        """Validate max results are within bounds"""
        if v is not None:
            if info.field_name == 'max_vendor_results' and v > MAX_VENDOR_RESULTS:
                raise ValueError(f"max_vendor_results cannot exceed {MAX_VENDOR_RESULTS}")
            if info.field_name == 'max_location_results' and v > MAX_LOCATION_RESULTS:
                raise ValueError(f"max_location_results cannot exceed {MAX_LOCATION_RESULTS}")
        return v


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


def detect_location_in_prompt(prompt: str) -> bool:
    """
    Detect if a location/place is mentioned in the prompt using common sense.
    Returns True if location is detected, False otherwise.
    """
    prompt_lower = prompt.lower()
    
    # Common location indicators
    location_keywords = [
        'in ', 'at ', 'near ', 'around ', 'location:', 'place:', 'city:', 
        'venue:', 'area:', 'region:', 'town:', 'downtown', 'city center',
        'suburb', 'district', 'neighborhood', 'province', 'state', 'country'
    ]
    
    # Common location prepositions patterns
    location_patterns = [
        ' in ', ' at ', ' near ', ' around ', ' from ', ' to '
    ]
    
    # Check for location keywords
    for keyword in location_keywords:
        if keyword in prompt_lower:
            return True
    
    # Check if there are city/place name patterns (capitalized words after location prepositions)
    words = prompt.split()
    for i, word in enumerate(words):
        if word.lower() in ['in', 'at', 'near', 'around', 'from', 'to']:
            # Check if next word is capitalized (likely a place name)
            if i + 1 < len(words) and words[i + 1][0].isupper():
                return True
    
    # Check for common place suffixes
    place_suffixes = ['city', 'town', 'beach', 'park', 'center', 'square', 'street', 'avenue', 'road']
    for suffix in place_suffixes:
        if suffix in prompt_lower:
            return True
    
    return False


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
    
    start_time = datetime.now()
    logger.info(f"Event planning request received: {request.prompt[:100]}...")
    
    if not request.prompt or not request.prompt.strip():
        logger.warning("Empty prompt received")
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    # Check if location is mentioned in the prompt
    if not detect_location_in_prompt(request.prompt):
        logger.info(f"Location not detected in prompt: {request.prompt}")
        return {
            "status": "location_required",
            "user_prompt": request.prompt,
            "recommendations": {
                "vendors": {
                    "status": "pending",
                    "vendors_found": 0,
                    "message": "Location required to search for vendors"
                },
                "locations": {
                    "status": "pending",
                    "locations_found": 0,
                    "message": "Location required to search for venues"
                }
            },
            "summary": "Location information is required to provide recommendations."
        }
    
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
            
            # Call vendor and location services in parallel first
            vendor_task = client.post(
                f"{VENDOR_SERVICE_URL}/api/vendors/recommend",
                json=vendor_payload
            )
            
            location_task = client.post(
                f"{LOCATION_SERVICE_URL}/api/locations/search",
                json=location_payload
            )
            
            # Wait for vendor and location responses
            vendor_response, location_response = await asyncio.gather(
                vendor_task,
                location_task,
                return_exceptions=True
            )
            
            # Process vendor service response
            vendor_data = {}
            if isinstance(vendor_response, Exception):
                logger.error(f"Vendor service error: {str(vendor_response)}")
                vendor_data = {
                    "status": "error",
                    "message": f"Vendor service error: {str(vendor_response)}",
                    "vendors_found": 0,
                    "vendors": []
                }
            elif vendor_response.status_code == 200:
                vendor_data = vendor_response.json()
                logger.info(f"Vendor service success: {vendor_data.get('vendors_found', 0)} vendors found")
            else:
                logger.warning(f"Vendor service returned status {vendor_response.status_code}")
                vendor_data = {
                    "status": "error",
                    "message": f"Vendor service returned status {vendor_response.status_code}",
                    "vendors_found": 0,
                    "vendors": []
                }
            
            # Process location service response
            location_data = {}
            if isinstance(location_response, Exception):
                logger.error(f"Location service error: {str(location_response)}")
                location_data = {
                    "status": "error",
                    "message": f"Location service error: {str(location_response)}",
                    "locations_found": 0,
                    "locations": []
                }
            elif location_response.status_code == 200:
                location_data = location_response.json()
                logger.info(f"Location service success: {location_data.get('locations_found', 0)} locations found")
            else:
                logger.warning(f"Location service returned status {location_response.status_code}")
                location_data = {
                    "status": "error",
                    "message": f"Location service returned status {location_response.status_code}",
                    "locations_found": 0,
                    "locations": []
                }
            
            # Check if we have any matches
            vendors_found = vendor_data.get("vendors_found", 0)
            locations_found = location_data.get("locations_found", 0)
            
            logger.info(f"Total matches: {vendors_found} vendors, {locations_found} locations")
            
            # Only generate image prompt if we have matches
            image_prompt = None
            if vendors_found > 0 or locations_found > 0:
                try:
                    logger.info("Generating image prompt...")
                    prompt_response = await client.post(
                        f"{IMAGE_SERVICE_URL}/api/images/enhance-prompt",
                        json={"prompt": request.prompt},
                        timeout=30.0
                    )
                    
                    if prompt_response.status_code == 200:
                        image_prompt_data = prompt_response.json()
                        image_prompt = image_prompt_data.get("enhanced_prompt", request.prompt)
                        logger.info("Image prompt generated successfully")
                    else:
                        logger.warning(f"Image service returned status {prompt_response.status_code}")
                except Exception as e:
                    logger.error(f"Image prompt generation failed: {str(e)}")
                    # If image prompt fails, just skip it
                    pass
            
            # Aggregate results
            result = {
                "status": "success",
                "user_prompt": request.prompt,
                "recommendations": {
                    "vendors": vendor_data,
                    "locations": location_data
                },
                "summary": generate_summary(vendor_data, location_data)
            }
            
            # Only add image_generation_prompt if we have matches
            if image_prompt:
                result["image_generation_prompt"] = image_prompt
            else:
                result["message"] = "No suitable recommendations found. Please try refining your search with more specific details or adjust your search criteria."
            
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Request completed in {elapsed_time:.2f}s")
            
            return result
            
        except httpx.TimeoutException as e:
            logger.error(f"Request timeout: {str(e)}")
            raise HTTPException(
                status_code=504,
                detail="Request timeout - services took too long to respond"
            )
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error in plan_event: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Internal server error occurred. Please try again later."
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
    """Image generation request schema for ComfyUI with Ollama enhancement"""
    prompt: str = Field(..., description="User's simple description or detailed prompt")
    enhance_prompt: bool = Field(
        default=True,
        description="Whether to enhance prompt using Ollama LLM"
    )
    event_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Event context (theme, colors, mood, event_type)"
    )
    width: int = Field(default=1024, ge=512, le=2048, description="Image width")
    height: int = Field(default=1024, ge=512, le=2048, description="Image height")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")
    upload_to_cloudinary: bool = Field(
        default=False,
        description="Whether to upload to Cloudinary (disabled by default - images returned as base64)"
    )
    
    # Additional parameters for frontend compatibility (ignored by image service)
    num_images: Optional[int] = Field(default=1, description="Number of images to generate")
    steps: Optional[int] = Field(default=None, description="Inference steps (ignored for Z-Image Turbo)")
    cfg_scale: Optional[float] = Field(default=None, description="CFG scale (ignored for Z-Image Turbo)")
    sampler_name: Optional[str] = Field(default=None, description="Sampler name (ignored)")
    scheduler: Optional[str] = Field(default=None, description="Scheduler (ignored)")
    denoise: Optional[float] = Field(default=None, description="Denoise strength (ignored)")
    use_refiner: Optional[bool] = Field(default=False, description="Use refiner (not needed for Z-Image Turbo)")


class PromptEnhancementRequest(BaseModel):
    """Request for prompt enhancement only"""
    prompt: str = Field(..., description="User's simple prompt")
    event_context: Optional[Dict[str, Any]] = None
    generate_variations: bool = Field(default=False)
    variation_count: int = Field(default=3, ge=1, le=5)


@app.post("/api/v1/images/generate", tags=["Images"])
async def generate_images(request: ImageGenerationRequest = Body(...)):
    """
    Generate images using ComfyUI (Z-Image Turbo) with Ollama prompt enhancement
    Returns complete result after generation with Cloudinary URL
    """
    logger.info(f"Image generation request: {request.prompt[:100]}...")
    
    async with httpx.AsyncClient(timeout=IMAGE_SERVICE_TIMEOUT) as client:
        try:
            response = await client.post(
                f"{IMAGE_SERVICE_URL}/api/images/generate",
                json=request.model_dump()
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Image generation successful")
                return result
            else:
                error_text = response.text
                logger.error(f"Image service error {response.status_code}: {error_text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Image service error: {error_text}"
                )
        
        except httpx.TimeoutException:
            logger.error("Image generation timeout")
            raise HTTPException(
                status_code=504,
                detail="Image generation timeout - please try again"
            )
        except httpx.RequestError as e:
            logger.error(f"Cannot reach image service: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"Cannot reach image service at {IMAGE_SERVICE_URL}. Please ensure the Image Service is running on port 8003."
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in image generation: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )



@app.post("/api/v1/images/enhance-prompt", tags=["Images"])
async def enhance_image_prompt(request: PromptEnhancementRequest = Body(...)):
    """
    Enhance a prompt for better image generation using Ollama LLM
    Returns the enhanced prompt and optional variations for user to review
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{IMAGE_SERVICE_URL}/api/images/enhance-prompt",
                json=request.model_dump()
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


@app.get("/api/v1/images/health", tags=["Images"])
async def check_image_service_health():
    """Check health status of ComfyUI and Ollama services"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{IMAGE_SERVICE_URL}/api/images/health")
            return response.json()
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "comfyui_connected": False,
                "ollama_connected": False
            }


@app.post("/api/v1/images/generate/stream", tags=["Images"])
async def generate_images_stream(request: ImageGenerationRequest = Body(...)):
    """
    Generate images with real-time streaming progress using Server-Sent Events (SSE)
    Compatible with Z-Image Turbo workflow
    """
    logger.info(f"Streaming image generation request: {request.prompt[:100]}...")
    
    async def event_generator():
        """Generate Server-Sent Events for streaming progress"""
        try:
            # Send initial progress
            yield f"data: {json.dumps({'message': 'Initializing image generation...', 'progress_percent': 0})}\n\n"
            await asyncio.sleep(0.1)
            
            # Send prompt enhancement progress
            if request.enhance_prompt:
                yield f"data: {json.dumps({'message': 'Enhancing prompt with AI...', 'progress_percent': 10})}\n\n"
                await asyncio.sleep(0.1)
            
            # Send generation start
            yield f"data: {json.dumps({'message': 'Generating image with ComfyUI...', 'progress_percent': 30})}\n\n"
            await asyncio.sleep(0.1)
            
            # Call the image service
            async with httpx.AsyncClient(timeout=IMAGE_SERVICE_TIMEOUT) as client:
                response = await client.post(
                    f"{IMAGE_SERVICE_URL}/api/images/generate",
                    json=request.model_dump()
                )
                
                if response.status_code != 200:
                    error_msg = response.text
                    logger.error(f"Image service error: {error_msg}")
                    yield f"data: {json.dumps({'status': 'error', 'message': error_msg})}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                
                result = response.json()
                logger.info("Image generation successful")
                
                # Send processing progress
                yield f"data: {json.dumps({'message': 'Processing generated image...', 'progress_percent': 80})}\n\n"
                await asyncio.sleep(0.1)
                
                # Convert response to frontend expected format
                if result.get('success') and result.get('image_url'):
                    image_url = result['image_url']
                    
                    # Extract base64 data if it's a data URL
                    if image_url.startswith('data:image/'):
                        # Format: data:image/png;base64,XXXXX
                        parts = image_url.split(',', 1)
                        if len(parts) == 2:
                            base64_data = parts[1]
                            image_format = 'png'  # Extract from data URL if needed
                            
                            # Send completed response in expected format
                            completion_data = {
                                'status': 'completed',
                                'message': 'Image generation complete!',
                                'progress_percent': 100,
                                'images': [{
                                    'format': image_format,
                                    'data': base64_data
                                }],
                                'metadata': {
                                    'prompt_id': result.get('prompt_id'),
                                    'seed': result.get('seed'),
                                    'original_prompt': result.get('original_prompt'),
                                    'enhanced_prompt': result.get('enhanced_prompt'),
                                    'generation_time_seconds': result.get('generation_time_seconds'),
                                    'cloudinary_url': result.get('cloudinary_public_id')
                                }
                            }
                            yield f"data: {json.dumps(completion_data)}\n\n"
                        else:
                            yield f"data: {json.dumps({'status': 'error', 'message': 'Invalid image data format'})}\n\n"
                    else:
                        # Cloudinary URL - download and convert to base64
                        try:
                            async with httpx.AsyncClient(timeout=30.0) as img_client:
                                img_response = await img_client.get(image_url)
                                if img_response.status_code == 200:
                                    base64_data = base64.b64encode(img_response.content).decode('utf-8')
                                    completion_data = {
                                        'status': 'completed',
                                        'message': 'Image generation complete!',
                                        'progress_percent': 100,
                                        'images': [{
                                            'format': 'png',
                                            'data': base64_data
                                        }],
                                        'metadata': {
                                            'cloudinary_url': image_url,
                                            'prompt_id': result.get('prompt_id'),
                                            'seed': result.get('seed')
                                        }
                                    }
                                    yield f"data: {json.dumps(completion_data)}\n\n"
                                else:
                                    yield f"data: {json.dumps({'status': 'error', 'message': 'Failed to download image from Cloudinary'})}\n\n"
                        except Exception as e:
                            logger.error(f"Error downloading from Cloudinary: {e}")
                            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
                else:
                    yield f"data: {json.dumps({'status': 'error', 'message': 'Image generation failed'})}\n\n"
                
        except httpx.TimeoutException:
            logger.error("Image generation timeout")
            yield f"data: {json.dumps({'status': 'error', 'message': 'Generation timeout - please try again'})}\n\n"
        except httpx.RequestError as e:
            logger.error(f"Cannot reach image service: {e}")
            yield f"data: {json.dumps({'status': 'error', 'message': f'Cannot reach image service. Please ensure it is running on port 8003.'})}\n\n"
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
        finally:
            # Send completion marker
            yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/v1/images/enhance-prompt", tags=["Images"])
async def enhance_image_prompt_legacy(prompt: str = Body(..., embed=True)):
    """
    Legacy endpoint for prompt enhancement (simplified)
    Use /api/v1/images/enhance-prompt with full request body for better results
    """
    request = PromptEnhancementRequest(prompt=prompt)
    return await enhance_image_prompt(request)


class EmailTemplateRequest(BaseModel):
    """Email template generation request"""
    user_prompt: str = Field(..., description="User's original event request")
    venue_name: str = Field(..., description="Selected venue name")
    venue_address: str = Field(..., description="Venue address")
    venue_rating: Optional[float] = None
    venue_phone: Optional[str] = None
    venue_email: Optional[str] = None


@app.post("/api/v1/generate-email-template", tags=["Planning"])
async def generate_email_template(request: EmailTemplateRequest = Body(...)):
    """
    Generate a personalized venue inquiry email using Llama 3.2
    Based on the user's event requirements and selected venue
    """
    logger.info(f"Generating email template for venue: {request.venue_name}")
    
    # Build comprehensive prompt for Llama
    llama_prompt = f"""You are a professional event planner writing a venue inquiry email.

USER'S EVENT REQUEST:
{request.user_prompt}

SELECTED VENUE:
- Name: {request.venue_name}
- Address: {request.venue_address}
- Rating: {request.venue_rating if request.venue_rating else 'N/A'}

YOUR TASK:
Generate a professional, personalized email to this venue based on the user's event request.

REQUIREMENTS:
1. Analyze the user's prompt to understand:
   - Event type (wedding, conference, birthday, corporate, etc.)
   - Approximate date/timeframe (if mentioned)
   - Guest count (if mentioned)
   - Special requirements (catering, AV, parking, etc.)

2. Create an email with:
   - Appropriate subject line
   - Professional greeting addressing the venue
   - Clear event description based on user's request
   - Specific questions relevant to this event type
   - Requirements checklist relevant to this event
   - Professional closing

3. Make it personalized - reference specific details from the user's request

4. Keep the tone professional but warm

5. Include placeholders [in brackets] for information the user needs to fill in

OUTPUT FORMAT:
Return ONLY a JSON object with this structure:
{{
  "subject": "your subject line here",
  "body": "your email body here"
}}

DO NOT include any other text outside the JSON.
Use \\n for line breaks in the body."""

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Call Ollama via image service (reusing existing infrastructure)
            ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
            response = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": "llama3.2:3b",
                    "prompt": llama_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 1000
                    }
                },
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get("response", "")
                
                # Extract JSON from response
                try:
                    # Try to find JSON in the response
                    json_start = generated_text.find('{')
                    json_end = generated_text.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        email_data = json.loads(generated_text[json_start:json_end])
                        
                        # Add venue contact info footer
                        footer = f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nVenue Contact Information:\n{request.venue_name}\n{request.venue_address}"
                        if request.venue_phone:
                            footer += f"\nPhone: {request.venue_phone}"
                        if request.venue_email:
                            footer += f"\nEmail: {request.venue_email}"
                        footer += "\n\nGenerated via GatherUp AI Event Planning Assistant"
                        
                        email_data["body"] = email_data.get("body", "") + footer
                        
                        logger.info("Email template generated successfully")
                        return email_data
                    else:
                        raise ValueError("No JSON found in response")
                        
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse Llama response as JSON: {e}")
                    # Fallback: return the raw response
                    return {
                        "subject": f"Event Inquiry - {request.venue_name}",
                        "body": generated_text
                    }
            else:
                logger.error(f"Ollama error: {response.status_code}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to generate email template"
                )
                
        except httpx.TimeoutException:
            logger.error("Email generation timeout")
            raise HTTPException(
                status_code=504,
                detail="Email generation timeout - please try again"
            )
        except httpx.RequestError as e:
            logger.error(f"Cannot reach Ollama: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"Cannot reach AI service. Please ensure Ollama is running on port 11434."
            )
        except Exception as e:
            logger.error(f"Email generation error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Email generation error: {str(e)}"
            )


# ============================================================================
# TASKS API - For Task Division Feature
# ============================================================================

class TaskRequest(BaseModel):
    """Single task model"""
    title: str = Field(..., description="Task title/name")
    description: str = Field(..., description="Task description/details")
    priority: str = Field(default="medium", description="Priority: low, medium, high")
    status: str = Field(default="not started", description="Status: not started, progress, complete, cancelled, late")
    startDate: datetime = Field(default_factory=datetime.utcnow, description="Start date")
    dueDate: datetime = Field(..., description="Due date")
    employeeAcc: str = Field(..., description="Employee account who will do this task")


class CreateTasksRequest(BaseModel):
    """Request to create multiple tasks"""
    eventID: str = Field(..., description="Event ID (MongoDB ObjectId string)")
    assignedToID: str = Field(..., description="User ID who is creating these tasks")
    tasks: List[TaskRequest] = Field(..., description="List of tasks to create")


@app.post("/api/v1/tasks/create", tags=["Tasks"])
async def create_tasks(request: CreateTasksRequest):
    """
    Create multiple tasks for an event
    Tasks will be saved to MongoDB Tasks collection
    """
    try:
        task_ids = TasksModel.create_multiple(
            tasks=[task.dict() for task in request.tasks],
            event_id=request.eventID,
            assigned_to_id=request.assignedToID
        )
        
        return {
            "success": True,
            "message": f"Created {len(task_ids)} tasks successfully",
            "task_ids": task_ids,
            "event_id": request.eventID
        }
    except Exception as e:
        logger.error(f"Failed to create tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create tasks: {str(e)}"
        )


@app.get("/api/v1/tasks/{event_id}", tags=["Tasks"])
async def get_tasks_by_event(event_id: str):
    """Get all tasks for a specific event"""
    try:
        tasks = TasksModel.get_by_event(event_id)
        return {
            "success": True,
            "event_id": event_id,
            "tasks": tasks,
            "count": len(tasks)
        }
    except Exception as e:
        logger.error(f"Failed to fetch tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MEDIA HISTORY API - For Generated Images with Cloudinary
# ============================================================================

class SaveMediaRequest(BaseModel):
    """Request to save generated media"""
    eventID: str = Field(..., description="Event ID (MongoDB ObjectId string)")
    images: List[str] = Field(..., description="List of base64 images or Cloudinary URLs")
    uploadToCloudinary: bool = Field(default=True, description="Whether to upload to Cloudinary")


@app.post("/api/v1/media/save", tags=["Media"])
async def save_generated_media(request: SaveMediaRequest):
    """
    Upload images to Cloudinary and save references to MongoDB
    """
    try:
        cloudinary_urls = []
        
        if request.uploadToCloudinary:
            # Upload each image to Cloudinary
            for idx, image_data in enumerate(request.images):
                try:
                    # Check if it's already a URL
                    if image_data.startswith('http'):
                        cloudinary_urls.append(image_data)
                    else:
                        # Upload base64 image to Cloudinary
                        result = upload_base64_image(
                            image_data,
                            folder="gatherup_events",
                            public_id=f"event_{request.eventID}_img_{idx}_{datetime.utcnow().timestamp()}"
                        )
                        cloudinary_urls.append(result["secure_url"])
                except Exception as upload_error:
                    logger.error(f"Failed to upload image {idx}: {upload_error}")
                    # Continue with other images
        else:
            cloudinary_urls = request.images
        
        # Save to MongoDB GeneratedMediaHistory
        media_ids = GeneratedMediaHistoryModel.create_multiple(
            media_links=cloudinary_urls,
            event_id_string=request.eventID
        )
        
        return {
            "success": True,
            "message": f"Saved {len(media_ids)} images successfully",
            "media_ids": media_ids,
            "cloudinary_urls": cloudinary_urls,
            "event_id": request.eventID
        }
    except Exception as e:
        logger.error(f"Failed to save media: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save media: {str(e)}"
        )


@app.get("/api/v1/media/{event_id}", tags=["Media"])
async def get_media_by_event(event_id: str):
    """Get all generated media for a specific event"""
    try:
        media = GeneratedMediaHistoryModel.get_by_event(event_id)
        return {
            "success": True,
            "event_id": event_id,
            "media": media,
            "count": len(media)
        }
    except Exception as e:
        logger.error(f"Failed to fetch media: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TASK GENERATION & EVENT SAVING TO MONGODB
# ============================================================================

class SaveEventDataRequest(BaseModel):
    """Request model for saving complete event generation data"""
    user_id: Optional[str] = Field("user_temp_123", description="User ID (dummy for now)")
    user_prompt: str = Field(..., description="Original user event planning request")
    email_subject: str = Field(..., description="Generated email subject")
    email_body: str = Field(..., description="Generated email body")
    selected_venue: Dict[str, Any] = Field(..., description="Selected venue details")
    selected_vendors: List[Dict[str, Any]] = Field(default=[], description="All recommended vendors")
    generated_images: List[str] = Field(default=[], description="Generated images in base64 format")
    image_prompt: Optional[str] = Field(None, description="Prompt used for image generation")
    event_date: Optional[str] = Field(None, description="Event date in ISO format")
    guest_count: Optional[int] = Field(None, description="Estimated guest count")


async def generate_task_checklist(user_prompt: str, venue_name: str, vendors: List[Dict]) -> List[Dict[str, Any]]:
    """Generate organizer task checklist using Llama 3.2"""
    
    vendor_list = "\n".join([f"- {v.get('vendorName')} ({v.get('vendorType')})" for v in vendors[:5]])
    
    llama_prompt = f"""You are an expert event planning assistant. Generate a comprehensive task checklist for the event organizer.

EVENT DETAILS:
{user_prompt}

VENUE: {venue_name}

VENDORS:
{vendor_list}

Generate a detailed, actionable task checklist organized by timeframes. Include specific tasks with realistic deadlines.

OUTPUT FORMAT (JSON only, no other text):
{{
  "tasks": [
    {{
      "task": "Confirm venue booking and pay deposit",
      "category": "Venue",
      "priority": "high",
      "deadline_days_before": 60,
      "completed": false
    }},
    {{
      "task": "Finalize guest list and send save-the-dates",
      "category": "Guests",
      "priority": "high",
      "deadline_days_before": 45,
      "completed": false
    }}
  ]
}}

Include tasks for: venue confirmation, vendor bookings, guest management, logistics, decorations, day-of coordination.
Return ONLY the JSON object, nothing else."""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            ollama_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
            response = await client.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": "llama3.2:3b",
                    "prompt": llama_prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "top_p": 0.9, "num_predict": 1500}
                },
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get("response", "")
                
                json_start = generated_text.find('{')
                json_end = generated_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    task_data = json.loads(generated_text[json_start:json_end])
                    return task_data.get("tasks", [])
                    
    except Exception as e:
        logger.error(f"Task generation error: {e}")
    
    # Fallback default tasks
    return [
        {"task": "Confirm venue booking", "category": "Venue", "priority": "high", "deadline_days_before": 60, "completed": False},
        {"task": "Book selected vendors", "category": "Vendors", "priority": "high", "deadline_days_before": 45, "completed": False},
        {"task": "Finalize guest list", "category": "Guests", "priority": "medium", "deadline_days_before": 30, "completed": False},
        {"task": "Send invitations", "category": "Guests", "priority": "medium", "deadline_days_before": 21, "completed": False},
        {"task": "Arrange transportation/parking", "category": "Logistics", "priority": "medium", "deadline_days_before": 14, "completed": False},
        {"task": "Final venue walkthrough", "category": "Venue", "priority": "high", "deadline_days_before": 7, "completed": False},
        {"task": "Confirm all vendor arrivals", "category": "Vendors", "priority": "high", "deadline_days_before": 3, "completed": False},
        {"task": "Prepare day-of timeline", "category": "Coordination", "priority": "high", "deadline_days_before": 2, "completed": False},
    ]


def extract_event_details_from_prompt(prompt: str) -> Dict[str, Any]:
    """Extract event type, date, and guest count from user prompt using heuristics"""
    import re
    from dateutil import parser as date_parser
    
    event_info = {
        "event_type": "event",
        "event_date": None,
        "guest_count": None
    }
    
    # Event type detection
    event_types = {
        "wedding": ["wedding", "marriage", "bride", "groom"],
        "birthday": ["birthday", "bday", "birth day"],
        "conference": ["conference", "summit", "seminar", "workshop"],
        "corporate": ["corporate", "business", "company", "professional"],
        "party": ["party", "celebration"],
        "meeting": ["meeting", "gathering"]
    }
    
    prompt_lower = prompt.lower()
    for event_type, keywords in event_types.items():
        if any(keyword in prompt_lower for keyword in keywords):
            event_info["event_type"] = event_type
            break
    
    # Guest count extraction
    guest_patterns = [
        r'(\d+)\s*(?:people|guests|attendees|persons)',
        r'(?:for|about|around)\s*(\d+)',
        r'(\d+)\s*(?:pax|participants)'
    ]
    for pattern in guest_patterns:
        match = re.search(pattern, prompt_lower)
        if match:
            event_info["guest_count"] = int(match.group(1))
            break
    
    # Date extraction (simple patterns)
    try:
        # Look for date patterns
        date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', prompt)
        if date_match:
            event_info["event_date"] = date_parser.parse(date_match.group())
    except:
        pass
    
    return event_info


@app.post("/api/v1/save-event-data")
async def save_event_data(request: SaveEventDataRequest):
    """
    Save complete event to MongoDB with real values
    
    - Extracts event details from user prompt
    - Uploads images to Cloudinary
    - Generates organizer task checklist
    - Saves to Events collection with proper structure
    - Returns event ID with cloudinary URLs
    """
    try:
        # Verify MongoDB connection
        if not verify_connection():
            raise HTTPException(status_code=503, detail="Database connection failed")
        
        logger.info(f"Saving event data for user: {request.user_id}")
        
        # Extract event details from prompt
        event_details = extract_event_details_from_prompt(request.user_prompt)
        
        # Use provided date or generate one (3 months from now)
        if request.event_date:
            try:
                event_date = datetime.fromisoformat(request.event_date.replace('Z', '+00:00'))
            except:
                event_date = datetime.utcnow() + timedelta(days=90)
        elif event_details["event_date"]:
            event_date = event_details["event_date"]
        else:
            event_date = datetime.utcnow() + timedelta(days=90)
        
        guest_count = request.guest_count or event_details["guest_count"] or 50
        
        # Upload images to Cloudinary
        uploaded_images = []
        for idx, base64_img in enumerate(request.generated_images):
            try:
                if base64_img.startswith('data:image'):
                    base64_img = base64_img.split(',')[1]
                
                cloudinary_result = upload_base64_image(
                    base64_img,
                    folder="gatherup/events",
                    public_id=f"event_{datetime.utcnow().timestamp()}_{idx}"
                )
                
                uploaded_images.append({
                    "url": cloudinary_result["url"],
                    "cloudinary_id": cloudinary_result["cloudinary_id"],
                    "width": cloudinary_result["width"],
                    "height": cloudinary_result["height"],
                    "uploaded_at": datetime.utcnow()
                })
                
            except Exception as img_error:
                logger.error(f"Image {idx} upload error: {str(img_error)}")
                continue
        
        # Generate organizer task checklist
        task_checklist = await generate_task_checklist(
            request.user_prompt,
            request.selected_venue.get("name", ""),
            request.selected_vendors
        )
        
        # Calculate budget estimate
        vendor_pricing = []
        for vendor in request.selected_vendors:
            pricing = vendor.get("pricing", "")
            if pricing and "$" in pricing:
                # Extract numbers from pricing strings
                import re
                numbers = re.findall(r'\d+', pricing.replace(',', ''))
                if numbers:
                    vendor_pricing.append(float(numbers[0]))
        
        budget_estimate = sum(vendor_pricing) if vendor_pricing else None
        
        # Create event in MongoDB
        event_id = EventModel.create(
            user_id=request.user_id,
            user_prompt=request.user_prompt,
            event_type=event_details["event_type"],
            event_date=event_date,
            guest_count=guest_count,
            venue=request.selected_venue,
            vendors=request.selected_vendors,
            images=uploaded_images,
            email_template={"subject": request.email_subject, "body": request.email_body},
            task_checklist=task_checklist,
            budget_estimate=budget_estimate
        )
        
        logger.info(f"Event created successfully: {event_id}")
        
        return {
            "success": True,
            "message": "Event saved successfully to MongoDB",
            "event_id": event_id,
            "event_type": event_details["event_type"],
            "event_date": event_date.isoformat(),
            "guest_count": guest_count,
            "images_uploaded": len(uploaded_images),
            "cloudinary_urls": [img["url"] for img in uploaded_images],
            "tasks_generated": len(task_checklist),
            "budget_estimate": budget_estimate,
            "vendors_count": len(request.selected_vendors)
        }
        
    except Exception as e:
        logger.error(f"Save event error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save event: {str(e)}")


@app.post("/api/v1/save-event-data-legacy")
async def save_event_data_legacy(request: SaveEventDataRequest):
    """Legacy endpoint - kept for backward compatibility"""
    """
    Save email template and generated event data to MongoDB
    
    - Uploads images to Cloudinary
    - Saves email template to email_templates collection
    - Saves complete event data to generated_events collection
    - Uses FIRST vendor only from selected vendors
    """
    try:
        # Verify MongoDB connection
        if not verify_connection():
            raise HTTPException(
                status_code=503,
                detail="Database connection failed"
            )
        
        # Upload images to Cloudinary
        uploaded_images = []
        for idx, base64_img in enumerate(request.generated_images):
            try:
                # Remove data URI prefix if present
                if base64_img.startswith('data:image'):
                    base64_img = base64_img.split(',')[1]
                
                cloudinary_result = upload_base64_image(
                    base64_img,
                    folder="gatherup/events",
                    public_id=f"event_{request.event_id or 'temp'}_{datetime.utcnow().timestamp()}_{idx}"
                )
                
                uploaded_images.append({
                    "url": cloudinary_result["url"],
                    "cloudinary_id": cloudinary_result["cloudinary_id"],
                    "prompt": request.image_prompt,
                    "width": cloudinary_result["width"],
                    "height": cloudinary_result["height"],
                })
                
            except Exception as img_error:
                logger.error(f"Image upload error for image {idx}: {str(img_error)}")
                # Continue with other images even if one fails
                continue
        
        # Save email template
        email_template_id = EmailTemplateModel.create(
            event_id=request.event_id,
            subject=request.email_subject,
            body=request.email_body,
            venue_info=request.selected_venue,
            user_prompt=request.user_prompt
        )
        
        # Get FIRST vendor only (most important one)
        first_vendor = request.selected_vendors[0] if request.selected_vendors else None
        
        # Save generated event with all data
        generated_event_id = GeneratedEventModel.create(
            event_id=request.event_id,
            user_prompt=request.user_prompt,
            selected_venue=request.selected_venue,
            selected_vendor=first_vendor,
            generated_images=uploaded_images,
            image_prompt=request.image_prompt or ""
        )
        
        return {
            "success": True,
            "message": "Event data saved successfully",
            "email_template_id": email_template_id,
            "generated_event_id": generated_event_id,
            "images_uploaded": len(uploaded_images),
            "cloudinary_urls": [img["url"] for img in uploaded_images]
        }
        
    except Exception as e:
        logger.error(f"Save event data error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save event data: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("GATEWAY_PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
