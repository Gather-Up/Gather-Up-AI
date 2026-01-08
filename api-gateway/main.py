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
from datetime import datetime
import html
import json
from database import EmailTemplateModel, GeneratedEventModel, verify_connection
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
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
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
                        params={"prompt": request.prompt},
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
    logger.info(f"Image generation request: {request.prompt[:100]}... | Quality: {'High' if request.use_refiner else 'Normal'}")
    
    async with httpx.AsyncClient(timeout=IMAGE_SERVICE_TIMEOUT) as client:
        try:
            response = await client.post(
                f"{IMAGE_SERVICE_URL}/api/images/generate",
                json=request.model_dump()
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Image generation successful: {len(result.get('images', []))} images generated")
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
                detail="Image generation timeout - please try with fewer steps or smaller images"
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
# SAVE EMAIL AND GENERATED EVENT TO MONGODB
# ============================================================================

class SaveEventDataRequest(BaseModel):
    """Request model for saving complete event generation data"""
    event_id: Optional[str] = Field(None, description="MongoDB Event ObjectId (if exists)")
    user_prompt: str = Field(..., description="Original user event planning request")
    email_subject: str = Field(..., description="Generated email subject")
    email_body: str = Field(..., description="Generated email body")
    selected_venue: Dict[str, Any] = Field(..., description="Selected venue details")
    selected_vendors: Optional[List[Dict[str, Any]]] = Field(default=[], description="All recommended vendors")
    generated_images: List[str] = Field(default=[], description="Generated images in base64 format")
    image_prompt: Optional[str] = Field(None, description="Prompt used for image generation")


@app.post("/api/v1/save-event-data")
async def save_event_data(request: SaveEventDataRequest):
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
