"""
Image Generation Routes
Handles API endpoints for SDXL image generation with streaming support
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import json
import random
import time
from typing import AsyncGenerator

from schemas import (
    ImageGenerationRequest,
    ImageGenerationResponse,
    ImageGenerationError,
    ProgressUpdate
)
from services.comfyui_service import comfyui_service
from services.llama_service import enhance_image_prompt, analyze_prompt_for_negative

router = APIRouter(prefix="/images", tags=["Image Generation"])


async def generate_images_with_stream(request: ImageGenerationRequest) -> AsyncGenerator[str, None]:
    """
    Generator function that yields Server-Sent Events for image generation progress
    Handles multiple images sequentially with progress updates
    """
    
    total_start_time = time.time()
    all_images = []
    enhanced_prompt = request.prompt
    
    try:
        # Step 1: Enhance prompt with Llama 3.2
        yield f"data: {json.dumps({'status': 'processing', 'message': 'Enhancing prompt with Llama 3.2...', 'progress_percent': 5})}\n\n"
        
        enhancement_result = enhance_image_prompt(request.prompt)
        enhanced_prompt = enhancement_result.get("enhanced_prompt", request.prompt)
        
        yield f"data: {json.dumps({'status': 'processing', 'message': f'Prompt enhanced! Generating {request.num_images} image(s)...', 'progress_percent': 10, 'enhanced_prompt': enhanced_prompt})}\n\n"
        
        # Generate seed(s) if not provided
        seeds = []
        if request.seed is not None:
            # Use provided seed and increment for multiple images
            seeds = [request.seed + i for i in range(request.num_images)]
        else:
            # Generate random seeds
            seeds = [random.randint(0, 2**32 - 1) for _ in range(request.num_images)]
        
        # Enhance negative prompt if needed
        if request.negative_prompt:
            negative_prompt = request.negative_prompt
        else:
            negative_prompt = analyze_prompt_for_negative(request.prompt)
        
        # Step 2: Generate each image sequentially
        for idx in range(request.num_images):
            image_num = idx + 1
            seed = seeds[idx]
            
            yield f"data: {json.dumps({'status': 'generating', 'message': f'Starting generation for image {image_num}/{request.num_images}...', 'image_index': image_num, 'progress_percent': 15 + (idx * 70 // request.num_images)})}\n\n"
            
            # Stream generation progress for this image
            async for progress in comfyui_service.generate_image_stream(
                prompt=enhanced_prompt,
                negative_prompt=negative_prompt,
                width=request.width,
                height=request.height,
                steps=request.steps,
                cfg_scale=request.cfg_scale,
                sampler_name=request.sampler_name.value,
                scheduler=request.scheduler.value,
                seed=seed,
                denoise=request.denoise,
                use_refiner=request.use_refiner
            ):
                # Add image index to progress
                progress['image_index'] = image_num
                progress['total_images'] = request.num_images
                
                # Adjust progress percent to account for multiple images
                if 'progress_percent' in progress:
                    base_progress = 15 + (idx * 70 // request.num_images)
                    image_progress = progress['progress_percent'] * 0.7 / request.num_images
                    progress['progress_percent'] = base_progress + image_progress
                
                yield f"data: {json.dumps(progress)}\n\n"
                
                # If completed, save the image data
                if progress.get('status') == 'completed' and progress.get('image_data'):
                    all_images.append({
                        'index': image_num,
                        'data': progress['image_data']['data'],
                        'filename': progress['image_data']['filename'],
                        'format': progress['image_data']['format'],
                        'seed': seed,
                        'generation_time': progress.get('generation_time', 0)
                    })
                
                # If error occurred, stop generation
                if progress.get('status') == 'error':
                    raise Exception(progress.get('error', 'Unknown error'))
            
            # Small delay between images
            if image_num < request.num_images:
                await asyncio.sleep(1)
        
        # Step 3: All images generated successfully
        total_time = time.time() - total_start_time
        
        final_response = {
            'status': 'completed',
            'message': f'Successfully generated {len(all_images)} image(s) in {total_time:.1f}s',
            'progress_percent': 100,
            'images': all_images,
            'enhanced_prompt': enhanced_prompt,
            'generation_params': {
                'width': request.width,
                'height': request.height,
                'steps': request.steps,
                'cfg_scale': request.cfg_scale,
                'sampler': request.sampler_name.value,
                'scheduler': request.scheduler.value,
                'seeds': seeds,
                'negative_prompt': negative_prompt
            },
            'total_generation_time': total_time
        }
        
        yield f"data: {json.dumps(final_response)}\n\n"
        yield "data: [DONE]\n\n"
    
    except Exception as e:
        error_response = {
            'status': 'error',
            'message': f'Error during image generation: {str(e)}',
            'error': str(e)
        }
        yield f"data: {json.dumps(error_response)}\n\n"
        yield "data: [DONE]\n\n"


@router.post("/generate/stream")
async def generate_images_stream(request: ImageGenerationRequest):
    """
    Generate images with real-time streaming progress updates (SSE)
    
    Returns Server-Sent Events stream with progress updates
    Perfect for frontend integration with real-time feedback
    """
    return StreamingResponse(
        generate_images_with_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable proxy buffering
        }
    )


@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_images(request: ImageGenerationRequest):
    """
    Generate images without streaming (waits for completion)
    
    Returns complete result after all images are generated
    Use this for simple integrations or when streaming is not needed
    """
    
    total_start_time = time.time()
    all_images = []
    
    try:
        # Enhance prompt with Llama
        enhancement_result = enhance_image_prompt(request.prompt)
        enhanced_prompt = enhancement_result.get("enhanced_prompt", request.prompt)
        
        # Generate seeds
        seeds = []
        if request.seed is not None:
            seeds = [request.seed + i for i in range(request.num_images)]
        else:
            seeds = [random.randint(0, 2**32 - 1) for _ in range(request.num_images)]
        
        # Enhance negative prompt
        negative_prompt = request.negative_prompt if request.negative_prompt else analyze_prompt_for_negative(request.prompt)
        
        # Generate each image
        for idx in range(request.num_images):
            seed = seeds[idx]
            
            # Collect all progress updates
            image_data = None
            generation_time = 0
            
            async for progress in comfyui_service.generate_image_stream(
                prompt=enhanced_prompt,
                negative_prompt=negative_prompt,
                width=request.width,
                height=request.height,
                steps=request.steps,
                cfg_scale=request.cfg_scale,
                sampler_name=request.sampler_name.value,
                scheduler=request.scheduler.value,
                seed=seed,
                denoise=request.denoise,
                use_refiner=request.use_refiner
            ):
                if progress.get('status') == 'completed' and progress.get('image_data'):
                    image_data = progress['image_data']
                    generation_time = progress.get('generation_time', 0)
                
                if progress.get('status') == 'error':
                    raise Exception(progress.get('error', 'Unknown error'))
            
            if image_data:
                all_images.append({
                    'index': idx + 1,
                    'data': image_data['data'],
                    'filename': image_data['filename'],
                    'format': image_data['format'],
                    'seed': seed,
                    'generation_time': generation_time
                })
        
        total_time = time.time() - total_start_time
        
        return ImageGenerationResponse(
            status="success",
            message=f"Successfully generated {len(all_images)} image(s)",
            images=all_images,
            enhanced_prompt=enhanced_prompt,
            generation_params={
                'width': request.width,
                'height': request.height,
                'steps': request.steps,
                'cfg_scale': request.cfg_scale,
                'sampler': request.sampler_name.value,
                'scheduler': request.scheduler.value,
                'seeds': seeds,
                'negative_prompt': negative_prompt
            },
            total_generation_time=total_time
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Image generation failed: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Check if ComfyUI is accessible"""
    is_healthy = await comfyui_service.check_comfyui_status()
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "comfyui_accessible": is_healthy,
        "comfyui_url": comfyui_service.base_url
    }


@router.post("/enhance-prompt")
async def enhance_prompt_only(prompt: str):
    """
    Enhance a prompt using Llama 3.2 without generating images
    Useful for testing prompt enhancement
    """
    result = enhance_image_prompt(prompt)
    return result
