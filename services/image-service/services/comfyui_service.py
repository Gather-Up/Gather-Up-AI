"""
ComfyUI API Integration Service
Handles communication with ComfyUI server for SDXL image generation
"""

import asyncio
import aiohttp
import json
import uuid
import base64
import time
from typing import Optional, AsyncGenerator
import os
from dotenv import load_dotenv

load_dotenv()

COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
COMFYUI_TIMEOUT = int(os.getenv("COMFYUI_TIMEOUT", "300"))

print(f"✓ ComfyUI Configuration:")
print(f"  - URL: {COMFYUI_URL}")
print(f"  - Timeout: {COMFYUI_TIMEOUT}s")


class ComfyUIService:
    """Service class for interacting with ComfyUI API"""
    
    def __init__(self, base_url: str = COMFYUI_URL):
        self.base_url = base_url.rstrip('/')
        self.client_id = str(uuid.uuid4())
    
    def get_sdxl_base_only_workflow(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        cfg_scale: float,
        sampler_name: str,
        scheduler: str,
        seed: int,
        denoise: float
    ) -> dict:
        """
        Generate ComfyUI workflow JSON for SDXL Base model only
        Faster generation, good quality
        """
        workflow = {
            # Load Base Model
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "sd_xl_base_1.0.safetensors"
                }
            },
            # Empty Latent Image
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                }
            },
            # Positive Prompt
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["4", 1]
                }
            },
            # Negative Prompt
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["4", 1]
                }
            },
            # KSampler
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg_scale,
                    "sampler_name": sampler_name,
                    "scheduler": scheduler,
                    "denoise": denoise,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                }
            },
            # VAE Decode
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                }
            },
            # Save Image
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "GatherUp_AI",
                    "images": ["8", 0]
                }
            }
        }
        return workflow
    
    def get_sdxl_workflow(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        cfg_scale: float,
        sampler_name: str,
        scheduler: str,
        seed: int,
        denoise: float,
        use_refiner: bool = True
    ) -> dict:
        """
        Generate ComfyUI workflow JSON for SDXL
        - use_refiner=True: Base + Refiner (best quality, slower)
        - use_refiner=False: Base only (faster, good quality)
        """
        if not use_refiner:
            return self.get_sdxl_base_only_workflow(
                prompt, negative_prompt, width, height, 
                steps, cfg_scale, sampler_name, scheduler, seed, denoise
            )
        
        # Base + Refiner workflow
        return self.get_sdxl_base_refiner_workflow(
            prompt, negative_prompt, width, height,
            steps, cfg_scale, sampler_name, scheduler, seed, denoise
        )
    
    def get_sdxl_base_refiner_workflow(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        cfg_scale: float,
        sampler_name: str,
        scheduler: str,
        seed: int,
        denoise: float
    ) -> dict:
        """
        Generate ComfyUI workflow JSON for SDXL Base + Refiner
        Uses both base and refiner models for highest quality output
        """
        # Split steps between base (80%) and refiner (20%)
        base_steps = int(steps * 0.8)
        refiner_steps = steps - base_steps
        
        workflow = {
            # Load Base Model
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "sd_xl_base_1.0.safetensors"
                }
            },
            # Load Refiner Model
            "10": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "sd_xl_refiner_1.0.safetensors"
                }
            },
            # Empty Latent Image
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                }
            },
            # Positive Prompt (Base)
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["4", 1]
                }
            },
            # Negative Prompt (Base)
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["4", 1]
                }
            },
            # Base KSampler (first 80% of steps)
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg_scale,
                    "sampler_name": sampler_name,
                    "scheduler": scheduler,
                    "denoise": denoise,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                }
            },
            # Positive Prompt (Refiner)
            "11": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["10", 1]
                }
            },
            # Negative Prompt (Refiner)
            "12": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": negative_prompt,
                    "clip": ["10", 1]
                }
            },
            # Refiner KSampler (final 20% of steps for detail enhancement)
            "13": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg_scale,
                    "sampler_name": sampler_name,
                    "scheduler": scheduler,
                    "denoise": 0.25,  # Refiner only touches up details
                    "model": ["10", 0],
                    "positive": ["11", 0],
                    "negative": ["12", 0],
                    "latent_image": ["3", 0]  # Takes output from base sampler
                }
            },
            # VAE Decode (decode refined latent to image)
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["13", 0],  # Use refiner output
                    "vae": ["10", 2]
                }
            },
            # Save Image
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "GatherUp_AI",
                    "images": ["8", 0]
                }
            }
        }
        return workflow
    
    async def check_comfyui_status(self) -> bool:
        """Check if ComfyUI server is running and accessible"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/system_stats", timeout=5) as response:
                    return response.status == 200
        except Exception as e:
            print(f"❌ ComfyUI connection error: {str(e)}")
            return False
    
    async def queue_prompt(self, workflow: dict) -> Optional[str]:
        """
        Queue a prompt to ComfyUI and return the prompt_id
        """
        try:
            payload = {
                "prompt": workflow,
                "client_id": self.client_id
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/prompt",
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        prompt_id = result.get("prompt_id")
                        print(f"✓ Queued prompt: {prompt_id}")
                        return prompt_id
                    else:
                        error_text = await response.text()
                        print(f"❌ Queue error: {error_text}")
                        return None
        except Exception as e:
            print(f"❌ Queue error: {str(e)}")
            return None
    
    async def get_history(self, prompt_id: str) -> Optional[dict]:
        """Get the history/result of a prompt"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/history/{prompt_id}") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get(prompt_id)
                    return None
        except Exception as e:
            print(f"❌ History fetch error: {str(e)}")
            return None
    
    async def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> Optional[bytes]:
        """Download generated image from ComfyUI"""
        try:
            params = {
                "filename": filename,
                "subfolder": subfolder,
                "type": folder_type
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/view", params=params) as response:
                    if response.status == 200:
                        return await response.read()
                    return None
        except Exception as e:
            print(f"❌ Image download error: {str(e)}")
            return None
    
    async def wait_for_completion(self, prompt_id: str, timeout: int = COMFYUI_TIMEOUT) -> Optional[dict]:
        """
        Wait for prompt to complete and return the result
        Polls every 2 seconds
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            history = await self.get_history(prompt_id)
            
            if history and "outputs" in history:
                return history
            
            # Wait before next check
            await asyncio.sleep(2)
        
        print(f"❌ Timeout waiting for prompt {prompt_id}")
        return None
    
    async def generate_image_stream(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        cfg_scale: float,
        sampler_name: str,
        scheduler: str,
        seed: int,
        denoise: float,
        use_refiner: bool = True
    ) -> AsyncGenerator[dict, None]:
        """
        Generate image with streaming progress updates
        Yields progress updates as they become available
        """
        
        # Initial status
        yield {
            "status": "queued",
            "message": "Preparing workflow for ComfyUI...",
            "progress_percent": 0
        }
        
        # Check if ComfyUI is running
        is_running = await self.check_comfyui_status()
        if not is_running:
            yield {
                "status": "error",
                "message": "ComfyUI server is not accessible. Please ensure ComfyUI is running.",
                "error": "Connection failed"
            }
            return
        
        # Generate workflow
        workflow = self.get_sdxl_workflow(
            prompt, negative_prompt, width, height,
            steps, cfg_scale, sampler_name, scheduler, seed, denoise, use_refiner
        )
        
        yield {
            "status": "queued",
            "message": "Submitting to ComfyUI queue...",
            "progress_percent": 10
        }
        
        # Queue the prompt
        prompt_id = await self.queue_prompt(workflow)
        if not prompt_id:
            yield {
                "status": "error",
                "message": "Failed to queue prompt in ComfyUI",
                "error": "Queue failed"
            }
            return
        
        yield {
            "status": "processing",
            "message": f"Queued in ComfyUI (ID: {prompt_id[:8]}...). Generation starting...",
            "progress_percent": 20
        }
        
        # Wait for completion with progress updates
        start_time = time.time()
        timeout = COMFYUI_TIMEOUT
        
        while time.time() - start_time < timeout:
            history = await self.get_history(prompt_id)
            
            if history and "outputs" in history:
                # Generation complete!
                elapsed_time = time.time() - start_time
                
                yield {
                    "status": "generating",
                    "message": f"Generation complete! Retrieving image...",
                    "progress_percent": 90
                }
                
                # Extract image information
                outputs = history["outputs"]
                images_data = []
                
                for node_id, node_output in outputs.items():
                    if "images" in node_output:
                        for image_info in node_output["images"]:
                            filename = image_info["filename"]
                            subfolder = image_info.get("subfolder", "")
                            
                            # Download image
                            image_bytes = await self.get_image(filename, subfolder)
                            
                            if image_bytes:
                                # Convert to base64 for transmission
                                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                                images_data.append({
                                    "filename": filename,
                                    "data": image_base64,
                                    "format": "png"
                                })
                
                yield {
                    "status": "completed",
                    "message": f"Image generated successfully in {elapsed_time:.1f}s",
                    "progress_percent": 100,
                    "image_data": images_data[0] if images_data else None,
                    "generation_time": elapsed_time
                }
                return
            
            # Still processing - send progress update
            elapsed = time.time() - start_time
            estimated_progress = min(85, 20 + (elapsed / timeout) * 65)
            
            yield {
                "status": "generating",
                "message": f"Generating image... ({int(elapsed)}s elapsed)",
                "progress_percent": estimated_progress,
                "current_step": None,
                "total_steps": steps
            }
            
            await asyncio.sleep(2)
        
        # Timeout
        yield {
            "status": "error",
            "message": f"Generation timed out after {timeout}s",
            "error": "Timeout"
        }


# Singleton instance
comfyui_service = ComfyUIService()
