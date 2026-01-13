"""
ComfyUI Client Service
Handles communication with ComfyUI server for image generation
"""

import httpx
import asyncio
import json
import os
import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ComfyUIClient:
    """Client for interacting with ComfyUI API"""
    
    def __init__(self, base_url: str, timeout: int = 300):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client_id = str(uuid.uuid4())
        
    async def check_connection(self) -> bool:
        """Check if ComfyUI server is accessible"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/system_stats")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to connect to ComfyUI: {e}")
            return False
    
    def create_workflow(
        self,
        prompt: str,
        text_encoder_model: str,
        diffusion_model: str,
        vae_model: str,
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create ComfyUI workflow for Z-Image Turbo
        Uses separate model files: UNET, DualCLIP, and VAE
        """
        if seed is None:
            seed = int(datetime.now().timestamp() * 1000000) % 2**32
        
        # Z-Image Turbo workflow - optimized for fast generation (4 steps)
        workflow = {
            "1": {  # Load UNET Model
                "inputs": {
                    "unet_name": "z_image_turbo_bf16.safetensors",
                    "weight_dtype": "default"
                },
                "class_type": "UNETLoader"
            },
            "2": {  # Load CLIP Model (Single)
                "inputs": {
                    "clip_name": "qwen_3_4b.safetensors",
                    "type": "sd3"
                },
                "class_type": "CLIPLoader"
            },
            "3": {  # Load VAE
                "inputs": {
                    "vae_name": "ae.safetensors"
                },
                "class_type": "VAELoader"
            },
            "4": {  # Positive Prompt
                "inputs": {
                    "text": prompt,
                    "clip": ["2", 0]
                },
                "class_type": "CLIPTextEncode"
            },
            "5": {  # Negative Prompt
                "inputs": {
                    "text": "",
                    "clip": ["2", 0]
                },
                "class_type": "CLIPTextEncode"
            },
            "6": {  # Empty Latent Image
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage"
            },
            "7": {  # KSampler (Z-Image Turbo settings: 4 steps, cfg=1.0)
                "inputs": {
                    "seed": seed,
                    "steps": 4,
                    "cfg": 1.0,
                    "sampler_name": "euler",
                    "scheduler": "simple",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["4", 0],
                    "negative": ["5", 0],
                    "latent_image": ["6", 0]
                },
                "class_type": "KSampler"
            },
            "8": {  # VAE Decode
                "inputs": {
                    "samples": ["7", 0],
                    "vae": ["3", 0]
                },
                "class_type": "VAEDecode"
            },
            "9": {  # Save Image
                "inputs": {
                    "filename_prefix": "gatherup_ai",
                    "images": ["8", 0]
                },
                "class_type": "SaveImage"
            }
        }
        
        return workflow
    
    async def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        """Queue a workflow for execution and return the prompt_id"""
        try:
            payload = {
                "prompt": workflow,
                "client_id": self.client_id
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/prompt",
                    json=payload
                )
                
                # Log error response for debugging
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"ComfyUI rejected workflow: {error_detail}")
                    logger.error(f"Workflow sent: {json.dumps(workflow, indent=2)}")
                
                response.raise_for_status()
                
                result = response.json()
                prompt_id = result.get("prompt_id")
                
                if not prompt_id:
                    raise ValueError("No prompt_id returned from ComfyUI")
                
                logger.info(f"Queued prompt with ID: {prompt_id}")
                return prompt_id
                
        except Exception as e:
            logger.error(f"Failed to queue prompt: {e}")
            raise
    
    async def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """Get execution history for a prompt"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/history/{prompt_id}"
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            raise
    
    async def wait_for_completion(
        self,
        prompt_id: str,
        check_interval: float = 1.0,
        max_wait_time: float = 300.0
    ) -> Dict[str, Any]:
        """Wait for workflow execution to complete"""
        start_time = asyncio.get_event_loop().time()
        success_found_at = None
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            
            if elapsed > max_wait_time:
                raise TimeoutError(f"Workflow execution timed out after {max_wait_time}s")
            
            try:
                history = await self.get_history(prompt_id)
                
                if prompt_id in history:
                    prompt_history = history[prompt_id]
                    
                    # Check for errors first
                    status = prompt_history.get("status", {})
                    status_str = status.get("status_str", "unknown")
                    
                    if status_str == "error":
                        error_msg = status.get("messages", [])
                        logger.error(f"Workflow failed with error: {error_msg}")
                        raise RuntimeError(f"Workflow failed: {error_msg}")
                    
                    # Check if we have outputs with actual content
                    outputs = prompt_history.get("outputs", {})
                    
                    # Look for SaveImage node output (node 9 in our workflow)
                    has_valid_output = False
                    if outputs and isinstance(outputs, dict):
                        for node_id, output in outputs.items():
                            if isinstance(output, dict) and "images" in output and output["images"]:
                                has_valid_output = True
                                break
                    
                    if has_valid_output:
                        logger.info(f"Workflow {prompt_id} completed with valid outputs: {list(outputs.keys())}")
                        return prompt_history
                    
                    # If marked success but no outputs yet, wait a bit more
                    if status_str == "success":
                        if success_found_at is None:
                            success_found_at = asyncio.get_event_loop().time()
                            logger.info(f"Workflow marked success, waiting for outputs to populate...")
                        
                        # Give it 15 more seconds after success to populate outputs
                        time_since_success = asyncio.get_event_loop().time() - success_found_at
                        if time_since_success > 15:
                            # Return what we have even if outputs are not ideal
                            logger.warning(f"Workflow success but outputs still not ready after 15s")
                            logger.warning(f"Outputs structure: {json.dumps(outputs, indent=2)[:500]}")
                            return prompt_history
                    
                    logger.debug(f"Waiting for workflow {prompt_id}... status: {status_str}")
                
            except Exception as e:
                logger.warning(f"Error checking history: {e}, retrying...")
            
            await asyncio.sleep(check_interval)
    
    async def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """Download generated image from ComfyUI"""
        try:
            params = {
                "filename": filename,
                "subfolder": subfolder,
                "type": folder_type
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/view",
                    params=params
                )
                response.raise_for_status()
                return response.content
                
        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            raise
    
    async def generate_image(
        self,
        prompt: str,
        text_encoder_model: str,
        diffusion_model: str,
        vae_model: str,
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Complete workflow: create, queue, wait, and retrieve image
        Returns: Dict with image_data (bytes) and metadata
        """
        try:
            # Check connection
            if not await self.check_connection():
                raise ConnectionError("Cannot connect to ComfyUI server")
            
            # Create workflow
            workflow = self.create_workflow(
                prompt=prompt,
                text_encoder_model=text_encoder_model,
                diffusion_model=diffusion_model,
                vae_model=vae_model,
                width=width,
                height=height,
                seed=seed
            )
            
            # Queue the prompt
            prompt_id = await self.queue_prompt(workflow)
            
            # Wait for completion
            history = await self.wait_for_completion(prompt_id)
            
            # Extract image information
            outputs = history.get("outputs", {})
            
            logger.info(f"[DEBUG] Processing history for prompt {prompt_id}")
            logger.info(f"[DEBUG] History has keys: {list(history.keys())}")
            logger.info(f"[DEBUG] Outputs type: {type(outputs)}")
            logger.info(f"[DEBUG] Outputs keys: {list(outputs.keys()) if isinstance(outputs, dict) else 'Not a dict'}")
            
            # Log each output node
            if isinstance(outputs, dict):
                for node_id, node_output in outputs.items():
                    logger.info(f"[DEBUG] Node {node_id}: type={type(node_output)}, keys={list(node_output.keys()) if isinstance(node_output, dict) else 'N/A'}")
                    if isinstance(node_output, dict) and "images" in node_output:
                        logger.info(f"[DEBUG]   -> Has 'images' key with {len(node_output['images'])} images")
            
            # If outputs are empty, try fetching history one more time
            if not outputs:
                logger.warning("[DEBUG] No outputs in history, fetching again...")
                await asyncio.sleep(2)
                history = await self.get_history(prompt_id)
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    logger.info(f"[DEBUG] Second fetch outputs: {outputs}")
            
            # Log the full history for debugging
            logger.info(f"[DEBUG] Final outputs to process: {json.dumps(outputs, indent=2)}")
            
            # Find the SaveImage node output (node "9" in our workflow)
            save_image_output = None
            for node_id in ["9", "7"]:  # Check node 9 first (Z-Image Turbo workflow)
                if node_id in outputs:
                    save_image_output = outputs[node_id]
                    logger.info(f"Found SaveImage output in node {node_id}")
                    break
            
            if not save_image_output:
                logger.error(f"No SaveImage node found in outputs. Available nodes: {list(outputs.keys())}")
                logger.error(f"Prompt ID: {prompt_id}")
                logger.error(f"Full history: {json.dumps(history, indent=2)[:500]}")
                
                # Try to get the image from ComfyUI's output folder directly
                logger.warning("Attempting to get most recent image from output folder...")
                try:
                    # List files in output directory
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        # Try getting the most recent gatherup_ai file
                        test_response = await client.get(
                            f"{self.base_url}/view",
                            params={"filename": "gatherup_ai_00001_.png", "type": "output"}
                        )
                        if test_response.status_code == 200:
                            logger.info("Found image in output folder!")
                            return {
                                "image_data": test_response.content,
                                "filename": "gatherup_ai_00001_.png",
                                "prompt_id": prompt_id,
                                "seed": seed,
                                "prompt": prompt,
                                "width": width,
                                "height": height
                            }
                except Exception as e:
                    logger.error(f"Could not retrieve image from output folder: {e}")
                
                raise ValueError("No SaveImage node in workflow outputs")
            
            images = save_image_output.get("images", [])
            
            if not images:
                logger.error(f"SaveImage node exists but has no images")
                logger.error(f"Save image output structure: {json.dumps(save_image_output, indent=2)}")
                
                # Try to list all outputs again
                logger.error(f"All outputs: {json.dumps(outputs, indent=2)}")
                
                raise ValueError(f"No images in SaveImage node output. Node had keys: {list(save_image_output.keys())}")
            
            # Get the first image
            image_info = images[0]
            filename = image_info["filename"]
            subfolder = image_info.get("subfolder", "")
            
            # Download the image
            image_data = await self.get_image(filename, subfolder)
            
            return {
                "image_data": image_data,
                "filename": filename,
                "prompt_id": prompt_id,
                "seed": seed,
                "prompt": prompt,
                "width": width,
                "height": height
            }
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise
    
    async def get_models(self) -> Dict[str, List[str]]:
        """Get available models from ComfyUI"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/object_info")
                response.raise_for_status()
                
                object_info = response.json()
                
                # Extract model lists
                checkpoints = object_info.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
                vae_models = object_info.get("VAELoader", {}).get("input", {}).get("required", {}).get("vae_name", [[]])[0]
                
                return {
                    "checkpoints": checkpoints,
                    "vae_models": vae_models
                }
        except Exception as e:
            logger.error(f"Failed to get models: {e}")
            return {"checkpoints": [], "vae_models": []}
