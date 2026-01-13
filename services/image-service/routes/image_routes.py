"""
Image Generation Routes
FastAPI endpoints for AI-powered image generation
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from fastapi.responses import StreamingResponse, JSONResponse
import logging
import os
import io
import time
from typing import Dict, Any
import base64

from schemas import (
    ImageGenerationRequest,
    ImageGenerationResponse,
    PromptEnhancementRequest,
    PromptEnhancementResponse,
    BatchImageGenerationRequest,
    BatchImageGenerationResponse,
    ServiceHealthResponse,
    ErrorResponse
)
from services.comfyui_client import ComfyUIClient
from services.ollama_service import OllamaService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/images", tags=["Image Generation"])

# Initialize services (will be set in main.py)
comfyui_client: ComfyUIClient = None
ollama_service: OllamaService = None
cloudinary_config: Dict[str, Any] = None


def init_services(comfyui: ComfyUIClient, ollama: OllamaService, cloudinary: Dict[str, Any]):
    """Initialize service instances"""
    global comfyui_client, ollama_service, cloudinary_config
    comfyui_client = comfyui
    ollama_service = ollama
    cloudinary_config = cloudinary


def has_valid_cloudinary_config() -> bool:
    """Check if Cloudinary credentials are properly configured"""
    if not cloudinary_config:
        return False
    
    cloud_name = cloudinary_config.get("cloud_name")
    api_key = cloudinary_config.get("api_key")
    api_secret = cloudinary_config.get("api_secret")
    
    # Check if credentials are set and not placeholder values
    if not cloud_name or not api_key or not api_secret:
        return False
    
    if api_key in ["your_api_key", "YOUR_API_KEY", ""] or \
       api_secret in ["your_api_secret", "YOUR_API_SECRET", ""] or \
       cloud_name in ["your_cloud_name", "YOUR_CLOUD_NAME", ""]:
        return False
    
    return True


async def upload_to_cloudinary(image_data: bytes, filename: str) -> Dict[str, str]:
    """Upload image to Cloudinary"""
    try:
        import cloudinary
        import cloudinary.uploader
        
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=cloudinary_config["cloud_name"],
            api_key=cloudinary_config["api_key"],
            api_secret=cloudinary_config["api_secret"]
        )
        
        # Upload image
        result = cloudinary.uploader.upload(
            image_data,
            folder="gatherup_ai",
            public_id=filename.replace(".png", ""),
            resource_type="image"
        )
        
        return {
            "url": result["secure_url"],
            "public_id": result["public_id"]
        }
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {e}")
        raise


@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest):
    """
    Generate an image from a text prompt using ComfyUI and Ollama
    
    Flow:
    1. Enhance prompt using Ollama LLM (if requested)
    2. Generate image using ComfyUI with Z-Image Turbo
    3. Upload to Cloudinary (if requested)
    4. Return image URL and metadata
    """
    start_time = time.time()
    
    try:
        # Step 1: Enhance prompt if requested
        original_prompt = request.prompt
        enhanced_prompt = request.prompt
        
        if request.enhance_prompt:
            logger.info("Enhancing prompt with Ollama...")
            enhancement_result = await ollama_service.enhance_prompt(
                user_input=request.prompt,
                event_context=request.event_context
            )
            enhanced_prompt = enhancement_result["enhanced_prompt"]
            logger.info(f"Prompt enhanced: {enhanced_prompt[:100]}...")
        
        # Step 2: Generate image with ComfyUI
        logger.info(f"Generating image with ComfyUI for prompt: {enhanced_prompt[:100]}...")
        
        try:
            generation_result = await comfyui_client.generate_image(
                prompt=enhanced_prompt,
                text_encoder_model=os.getenv("TEXT_ENCODER_MODEL", "qwen_3_4b.safetensors"),
                diffusion_model=os.getenv("DIFFUSION_MODEL", "z_image_turbo_bf16.safetensors"),
                vae_model=os.getenv("VAE_MODEL", "ae.safetensors"),
                width=request.width,
                height=request.height,
                seed=request.seed
            )
        except Exception as comfy_error:
            logger.error(f"ComfyUI generation error: {comfy_error}", exc_info=True)
            raise
        
        logger.info(f"Image generated successfully: {len(generation_result.get('image_data', b''))} bytes")
        
        image_data = generation_result["image_data"]
        filename = generation_result["filename"]
        prompt_id = generation_result["prompt_id"]
        seed = generation_result["seed"]
        
        # Step 3: Upload to Cloudinary if requested AND credentials are valid
        image_url = None
        cloudinary_public_id = None
        
        # Always encode to base64 for UI display
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        image_url = f"data:image/png;base64,{image_base64}"
        
        # Optionally upload to Cloudinary if requested and configured
        if request.upload_to_cloudinary and has_valid_cloudinary_config():
            try:
                logger.info("Uploading to Cloudinary...")
                cloudinary_result = await upload_to_cloudinary(image_data, filename)
                cloudinary_public_id = cloudinary_result["public_id"]
                logger.info(f"Image uploaded to Cloudinary: {cloudinary_result['url']}")
            except Exception as cloudinary_error:
                logger.warning(f"Cloudinary upload failed, continuing with base64: {cloudinary_error}")
                # Don't fail the request if Cloudinary upload fails
        
        generation_time = time.time() - start_time
        
        return ImageGenerationResponse(
            success=True,
            message="Image generated successfully",
            image_url=image_url,
            cloudinary_public_id=cloudinary_public_id,
            original_prompt=original_prompt,
            enhanced_prompt=enhanced_prompt if request.enhance_prompt else None,
            seed=seed,
            width=request.width,
            height=request.height,
            generation_time_seconds=round(generation_time, 2),
            prompt_id=prompt_id
        )
        
    except Exception as e:
        logger.error(f"Image generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image generation failed: {str(e)}"
        )


@router.post("/enhance-prompt", response_model=PromptEnhancementResponse)
async def enhance_prompt(request: PromptEnhancementRequest):
    """
    Enhance a simple prompt into a detailed image generation prompt
    This endpoint allows the frontend to show the enhanced prompt before generation
    """
    try:
        if request.generate_variations:
            # Generate multiple variations
            variations_result = await ollama_service.generate_multiple_variations(
                user_input=request.prompt,
                event_context=request.event_context,
                count=request.variation_count
            )
            
            # Return first as main, others as variations
            main = variations_result[0]
            variations = [v["enhanced_prompt"] for v in variations_result[1:]]
            
            return PromptEnhancementResponse(
                original_prompt=request.prompt,
                enhanced_prompt=main["enhanced_prompt"],
                variations=variations if variations else None
            )
        else:
            # Single prompt enhancement
            result = await ollama_service.enhance_prompt(
                user_input=request.prompt,
                event_context=request.event_context
            )
            
            # Optionally analyze quality
            quality_analysis = None
            if request.event_context and request.event_context.get("analyze_quality"):
                quality_analysis = await ollama_service.analyze_prompt_quality(
                    result["enhanced_prompt"]
                )
            
            return PromptEnhancementResponse(
                original_prompt=result["original_prompt"],
                enhanced_prompt=result["enhanced_prompt"],
                quality_analysis=quality_analysis
            )
            
    except Exception as e:
        logger.error(f"Prompt enhancement failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prompt enhancement failed: {str(e)}"
        )


@router.post("/generate-batch", response_model=BatchImageGenerationResponse)
async def generate_batch(request: BatchImageGenerationRequest, background_tasks: BackgroundTasks):
    """
    Generate multiple images from a batch of prompts
    Useful for creating multiple design options
    """
    start_time = time.time()
    results = []
    successful = 0
    failed = 0
    
    for prompt in request.prompts:
        try:
            # Create individual request
            individual_request = ImageGenerationRequest(
                prompt=prompt,
                enhance_prompt=request.enhance_prompts,
                event_context=request.event_context,
                width=request.width,
                height=request.height,
                upload_to_cloudinary=request.upload_to_cloudinary
            )
            
            # Generate image
            result = await generate_image(individual_request)
            results.append(result)
            successful += 1
            
        except Exception as e:
            logger.error(f"Failed to generate image for prompt '{prompt}': {e}")
            # Add error result
            results.append(ImageGenerationResponse(
                success=False,
                message=f"Generation failed: {str(e)}",
                original_prompt=prompt,
                width=request.width,
                height=request.height,
                generation_time_seconds=0.0,
                prompt_id="",
                seed=None
            ))
            failed += 1
    
    total_time = time.time() - start_time
    
    return BatchImageGenerationResponse(
        total_requested=len(request.prompts),
        successful=successful,
        failed=failed,
        results=results,
        total_time_seconds=round(total_time, 2)
    )


@router.get("/health", response_model=ServiceHealthResponse)
async def health_check():
    """
    Check the health of ComfyUI and Ollama services
    """
    try:
        comfyui_connected = await comfyui_client.check_connection()
        ollama_connected = await ollama_service.check_connection()
        
        available_models = None
        if comfyui_connected:
            available_models = await comfyui_client.get_models()
        
        status_str = "healthy" if (comfyui_connected and ollama_connected) else "degraded"
        
        return ServiceHealthResponse(
            status=status_str,
            comfyui_connected=comfyui_connected,
            ollama_connected=ollama_connected,
            available_models=available_models
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return ServiceHealthResponse(
            status="unhealthy",
            comfyui_connected=False,
            ollama_connected=False
        )


@router.get("/models")
async def get_available_models():
    """Get list of available models from ComfyUI"""
    try:
        models = await comfyui_client.get_models()
        return {
            "success": True,
            "models": models
        }
    except Exception as e:
        logger.error(f"Failed to get models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve models: {str(e)}"
        )


@router.get("/config")
async def get_service_config():
    """Get current service configuration (non-sensitive info only)"""
    return {
        "comfyui_url": os.getenv("COMFYUI_URL"),
        "ollama_url": os.getenv("OLLAMA_URL"),
        "ollama_model": os.getenv("OLLAMA_MODEL"),
        "default_image_size": {
            "width": int(os.getenv("DEFAULT_IMAGE_WIDTH", 1024)),
            "height": int(os.getenv("DEFAULT_IMAGE_HEIGHT", 1024))
        },
        "models": {
            "text_encoder": os.getenv("TEXT_ENCODER_MODEL"),
            "diffusion": os.getenv("DIFFUSION_MODEL"),
            "vae": os.getenv("VAE_MODEL")
        }
    }
