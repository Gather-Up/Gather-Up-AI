from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


class SamplerName(str, Enum):
    """Available samplers in ComfyUI"""
    EULER = "euler"
    EULER_ANCESTRAL = "euler_ancestral"
    HEUN = "heun"
    DPM_2 = "dpm_2"
    DPM_2_ANCESTRAL = "dpm_2_ancestral"
    LMS = "lms"
    DPM_FAST = "dpm_fast"
    DPM_ADAPTIVE = "dpm_adaptive"
    DPMPP_2S_ANCESTRAL = "dpmpp_2s_ancestral"
    DPMPP_SDE = "dpmpp_sde"
    DPMPP_2M = "dpmpp_2m"
    DPMPP_2M_SDE = "dpmpp_2m_sde"
    DDIM = "ddim"
    UNI_PC = "uni_pc"


class SchedulerName(str, Enum):
    """Available schedulers in ComfyUI"""
    NORMAL = "normal"
    KARRAS = "karras"
    EXPONENTIAL = "exponential"
    SGM_UNIFORM = "sgm_uniform"
    SIMPLE = "simple"
    DDIM_UNIFORM = "ddim_uniform"


class ImageGenerationRequest(BaseModel):
    """Request schema for image generation with Zephyr Image Turbo"""
    
    # User prompt (will be enhanced by cloud-based LLM)
    prompt: str = Field(..., description="Natural language description of the image to generate")
    
    # Number of images to generate (max 3)
    num_images: int = Field(default=1, ge=1, le=3, description="Number of images to generate (1-3)")
    
    # Core generation parameters
    negative_prompt: Optional[str] = Field(
        default="blurry, low quality, distorted, deformed, ugly, bad anatomy, bad proportions, watermark, text, logo",
        description="What to avoid in the image"
    )
    
    width: int = Field(default=1024, ge=512, le=2048, description="Image width (optimal: 1024)")
    height: int = Field(default=1024, ge=512, le=2048, description="Image height (optimal: 1024)")
    
    # Generation quality parameters (optimized for Zephyr Image Turbo)
    steps: int = Field(default=20, ge=8, le=50, description="Number of denoising steps (15-25 recommended for turbo)")
    cfg_scale: float = Field(default=5.0, ge=1.0, le=10.0, description="Classifier-free guidance scale (4-6 recommended for turbo)")
    
    # Sampler and scheduler (optimized for Zephyr Image Turbo)
    sampler_name: SamplerName = Field(default=SamplerName.EULER_ANCESTRAL, description="Sampling method (euler_ancestral best for turbo)")
    scheduler: SchedulerName = Field(default=SchedulerName.SIMPLE, description="Noise schedule (simple best for turbo)")
    
    # Seed for reproducibility
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility (None = random)")
    
    # Model selection (kept for compatibility, but refiner not used in turbo model)
    use_refiner: bool = Field(
        default=False, 
        description="Refiner not applicable for Zephyr Image Turbo (kept for API compatibility)"
    )
    
    # Denoise strength
    denoise: float = Field(default=1.0, ge=0.0, le=1.0, description="Denoising strength (1.0 = full generation)")


class ImageGenerationResponse(BaseModel):
    """Response schema for successful image generation"""
    status: Literal["success"] = "success"
    message: str
    images: list[dict] = Field(description="List of generated image data")
    enhanced_prompt: str = Field(description="Llama-enhanced prompt used for generation")
    generation_params: dict = Field(description="Parameters used for generation")
    total_generation_time: float = Field(description="Total time taken in seconds")


class ImageGenerationError(BaseModel):
    """Error response schema"""
    status: Literal["error"] = "error"
    message: str
    error_details: Optional[str] = None


class ProgressUpdate(BaseModel):
    """Progress update for streaming"""
    status: Literal["queued", "processing", "generating", "completed", "error"]
    message: str
    image_index: Optional[int] = None
    progress_percent: Optional[float] = None
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    image_data: Optional[dict] = None
    error: Optional[str] = None
