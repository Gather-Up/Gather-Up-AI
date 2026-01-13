"""
Pydantic schemas for Image Service API
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ImageGenerationRequest(BaseModel):
    """Request model for image generation"""
    prompt: str = Field(..., description="User's simple description or enhanced prompt")
    enhance_prompt: bool = Field(
        default=True,
        description="Whether to enhance the prompt using Ollama LLM"
    )
    event_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional event context (theme, colors, mood, etc.)"
    )
    width: int = Field(default=1024, ge=512, le=2048, description="Image width")
    height: int = Field(default=1024, ge=512, le=2048, description="Image height")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")
    upload_to_cloudinary: bool = Field(
        default=True,
        description="Whether to upload the generated image to Cloudinary"
    )


class PromptEnhancementRequest(BaseModel):
    """Request model for prompt enhancement only"""
    prompt: str = Field(..., description="User's simple prompt to enhance")
    event_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional event context"
    )
    generate_variations: bool = Field(
        default=False,
        description="Generate multiple prompt variations"
    )
    variation_count: int = Field(default=3, ge=1, le=5, description="Number of variations")


class PromptEnhancementResponse(BaseModel):
    """Response model for prompt enhancement"""
    original_prompt: str
    enhanced_prompt: str
    variations: Optional[List[str]] = None
    quality_analysis: Optional[Dict[str, Any]] = None


class ImageGenerationResponse(BaseModel):
    """Response model for image generation"""
    success: bool
    message: str
    image_url: Optional[str] = None
    cloudinary_public_id: Optional[str] = None
    original_prompt: str
    enhanced_prompt: Optional[str] = None
    seed: Optional[int] = None
    width: int
    height: int
    generation_time_seconds: float
    prompt_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BatchImageGenerationRequest(BaseModel):
    """Request model for batch image generation"""
    prompts: List[str] = Field(..., min_length=1, max_length=10)
    enhance_prompts: bool = Field(default=True)
    event_context: Optional[Dict[str, Any]] = None
    width: int = Field(default=1024, ge=512, le=2048)
    height: int = Field(default=1024, ge=512, le=2048)
    upload_to_cloudinary: bool = Field(default=True)


class BatchImageGenerationResponse(BaseModel):
    """Response model for batch image generation"""
    total_requested: int
    successful: int
    failed: int
    results: List[ImageGenerationResponse]
    total_time_seconds: float


class ServiceHealthResponse(BaseModel):
    """Health check response"""
    status: str
    comfyui_connected: bool
    ollama_connected: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    available_models: Optional[Dict[str, List[str]]] = None


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    details: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
