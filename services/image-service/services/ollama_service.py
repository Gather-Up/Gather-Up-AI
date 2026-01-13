"""
Ollama Service for Prompt Enhancement
Uses cloud-based Ollama LLM (same as vendor service) to enhance user prompts for better image generation
"""

import httpx
import requests
import logging
import json
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Cloud-based Ollama configuration (Same as vendor service)
OLLAMA_CLOUD_URL = os.getenv("OLLAMA_CLOUD_URL", "https://ollama.ai")
CLOUD_MODEL_NAME = os.getenv("OLLAMA_CLOUD_MODEL", "glm-4.6:cloud")

# Fallback to local if needed
USE_LOCAL_FALLBACK = os.getenv("USE_LOCAL_OLLAMA_FALLBACK", "false").lower() == "true"
OLLAMA_LOCAL_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
LOCAL_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "llama3.2:3b")

# Cloud configuration
CLOUD_CONFIG = {
    "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
    "top_p": float(os.getenv("OLLAMA_TOP_P", "0.9")),
    "top_k": int(os.getenv("OLLAMA_TOP_K", "40")),
    "repeat_penalty": float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.1")),
    "num_predict": 300  # Limit for faster responses
}

OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))
ENABLE_LLM_FALLBACK = os.getenv("ENABLE_LLM_FALLBACK", "true").lower() == "true"

logger.info(f"✓ Cloud-based LLM Configuration for Image Service:")
logger.info(f"  - Cloud Model: {CLOUD_MODEL_NAME} @ {OLLAMA_CLOUD_URL}")
if USE_LOCAL_FALLBACK:
    logger.info(f"  - Local Fallback: {LOCAL_MODEL_NAME} @ {OLLAMA_LOCAL_URL}")
logger.info(f"  - Temperature: {CLOUD_CONFIG['temperature']}")
logger.info(f"  - Timeout: {OLLAMA_TIMEOUT}s")


class OllamaService:
    """Service for interacting with cloud-based Ollama LLM"""
    
    def __init__(self):
        self.cloud_url = OLLAMA_CLOUD_URL
        self.cloud_model = CLOUD_MODEL_NAME
        self.local_url = OLLAMA_LOCAL_URL
        self.local_model = LOCAL_MODEL_NAME
        self.use_fallback = USE_LOCAL_FALLBACK
        self.timeout = OLLAMA_TIMEOUT
    
    async def check_connection(self) -> bool:
        """Check if cloud-based Ollama is accessible"""
        try:
            # Try cloud first
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.cloud_url}/api/tags")
                if response.status_code == 200:
                    logger.info("✓ Cloud Ollama connected")
                    return True
            
            # Try local fallback if enabled
            if self.use_fallback:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{self.local_url}/api/tags")
                    if response.status_code == 200:
                        logger.info("✓ Local Ollama fallback connected")
                        return True
            
            return False
        except Exception as e:
            logger.error(f"Ollama connection check failed: {e}")
            return False
    
    async def enhance_prompt(
        self,
        user_input: str,
        event_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Enhance a simple user prompt into a detailed image generation prompt using cloud-based LLM
        
        Args:
            user_input: Simple user description (e.g., "birthday party")
            event_context: Optional context about the event (theme, colors, etc.)
        
        Returns:
            Dict with enhanced_prompt and original_prompt
        """
        try:
            # Build context-aware system prompt
            system_context = self._build_system_prompt(event_context)
            
            # Create the enhancement request
            llm_prompt = f"""{system_context}

User wants to create an image for: "{user_input}"

Create a detailed, vivid image generation prompt that:
1. Describes the scene in rich visual detail
2. Specifies composition, lighting, and colors
3. Maintains professional quality for social media
4. Is optimized for AI image generation (like Z-Image Turbo)
5. Keeps the Instagram-ready aesthetic

Generate ONLY the enhanced prompt (max 200 words), no explanations."""

            # Try cloud-based Ollama first
            try:
                response = requests.post(
                    f"{self.cloud_url}/api/generate",
                    json={
                        "model": self.cloud_model,
                        "prompt": llm_prompt,
                        "stream": False,
                        "options": CLOUD_CONFIG
                    },
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    enhanced_prompt = result.get('response', '').strip()
                    
                    if not enhanced_prompt:
                        logger.warning("Cloud LLM returned empty prompt, using fallback")
                        raise Exception("Empty response from cloud LLM")
                    
                    logger.info(f"✓ Prompt enhanced using cloud model: {enhanced_prompt[:100]}...")
                    
                    return {
                        "original_prompt": user_input,
                        "enhanced_prompt": enhanced_prompt,
                        "model_used": self.cloud_model
                    }
                else:
                    logger.warning(f"Cloud API returned {response.status_code}")
                    raise Exception(f"Cloud API error: {response.status_code}")
            
            except Exception as cloud_error:
                logger.warning(f"Cloud LLM failed: {str(cloud_error)}")
                
                # Try local fallback if enabled
                if self.use_fallback and ENABLE_LLM_FALLBACK:
                    logger.info("Trying local Ollama fallback...")
                    try:
                        local_response = requests.post(
                            f"{self.local_url}/api/generate",
                            json={
                                "model": self.local_model,
                                "prompt": llm_prompt,
                                "stream": False,
                                "options": CLOUD_CONFIG
                            },
                            timeout=self.timeout
                        )
                        
                        if local_response.status_code == 200:
                            result = local_response.json()
                            enhanced_prompt = result.get('response', '').strip()
                            
                            if enhanced_prompt:
                                logger.info("✓ Prompt enhanced using local fallback")
                                return {
                                    "original_prompt": user_input,
                                    "enhanced_prompt": enhanced_prompt,
                                    "model_used": f"{self.local_model} (fallback)"
                                }
                    except Exception as local_error:
                        logger.warning(f"Local fallback failed: {str(local_error)}")
                
                # Use fallback prompt if both fail
                logger.info("Using fallback prompt enhancement")
                return {
                    "original_prompt": user_input,
                    "enhanced_prompt": self._create_fallback_prompt(user_input, event_context),
                    "model_used": "fallback"
                }
                
        except Exception as e:
            logger.error(f"Prompt enhancement failed: {e}")
            # Return fallback prompt
            return {
                "original_prompt": user_input,
                "enhanced_prompt": self._create_fallback_prompt(user_input, event_context),
                "model_used": "fallback"
            }
    
    def _build_system_prompt(self, event_context: Optional[Dict[str, Any]] = None) -> str:
        """Build system prompt based on event context"""
        base_prompt = """You are an expert AI prompt engineer specializing in creating detailed prompts for image generation models. Your prompts create stunning, professional-quality images perfect for social media and event marketing.

Focus on:
- Visual composition and framing
- Lighting and atmosphere
- Color schemes and harmony
- Professional quality and Instagram-ready aesthetics
- Specific details that make images pop"""
        
        if event_context:
            context_details = []
            
            if event_context.get("event_type"):
                context_details.append(f"Event Type: {event_context['event_type']}")
            
            if event_context.get("theme"):
                context_details.append(f"Theme: {event_context['theme']}")
            
            if event_context.get("color_scheme"):
                context_details.append(f"Color Scheme: {event_context['color_scheme']}")
            
            if event_context.get("mood"):
                context_details.append(f"Mood: {event_context['mood']}")
            
            if context_details:
                base_prompt += f"\n\nEvent Context:\n" + "\n".join(context_details)
        
        return base_prompt
    
    def _create_fallback_prompt(
        self,
        user_input: str,
        event_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a fallback prompt if LLM fails"""
        
        # Basic enhancement
        prompt_parts = [
            f"Professional social media post design for {user_input}",
            "vibrant colors and dynamic lighting",
            "high resolution",
            "balanced composition",
            "Instagram-ready aesthetic",
            "eye-catching visual design"
        ]
        
        # Add context if available
        if event_context:
            if event_context.get("theme"):
                prompt_parts.insert(1, f"theme: {event_context['theme']}")
            
            if event_context.get("color_scheme"):
                prompt_parts.insert(2, f"colors: {event_context['color_scheme']}")
        
        return ", ".join(prompt_parts)
    
    async def generate_multiple_variations(
        self,
        user_input: str,
        event_context: Optional[Dict[str, Any]] = None,
        count: int = 3
    ) -> list[Dict[str, str]]:
        """
        Generate multiple prompt variations for diverse results
        """
        try:
            system_context = self._build_system_prompt(event_context)
            
            llm_prompt = f"""{system_context}

Create {count} different detailed image generation prompts for: "{user_input}"

Each prompt should:
- Offer a unique creative interpretation
- Be detailed and vivid
- Be optimized for AI image generation
- Maintain professional quality

Provide ONLY the prompts, one per line, numbered 1-{count}."""

            # Try cloud API
            try:
                response = requests.post(
                    f"{self.cloud_url}/api/generate",
                    json={
                        "model": self.cloud_model,
                        "prompt": llm_prompt,
                        "stream": False,
                        "options": {**CLOUD_CONFIG, "num_predict": 500}
                    },
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get('response', '').strip()
                    
                    # Parse numbered lines
                    variations = []
                    for line in content.split('\n'):
                        line = line.strip()
                        if line and any(line.startswith(f"{i}.") for i in range(1, count + 1)):
                            # Remove number prefix
                            prompt = line.split('.', 1)[1].strip() if '.' in line else line
                            if prompt:
                                variations.append({
                                    "original_prompt": user_input,
                                    "enhanced_prompt": prompt,
                                    "variation_index": len(variations) + 1
                                })
                    
                    if variations:
                        return variations[:count]
            except Exception as e:
                logger.warning(f"Variations generation failed: {e}")
            
            # Fallback: generate single prompt
            single = await self.enhance_prompt(user_input, event_context)
            return [single]
                
        except Exception as e:
            logger.error(f"Failed to generate variations: {e}")
            single = await self.enhance_prompt(user_input, event_context)
            return [single]
    
    async def analyze_prompt_quality(self, prompt: str) -> Dict[str, Any]:
        """
        Analyze the quality and completeness of an image generation prompt
        Returns quality score and suggestions
        """
        try:
            analysis_prompt = f"""Analyze this image generation prompt for quality:

"{prompt}"

Provide a brief analysis (max 100 words) covering:
1. Quality score (0-10)
2. Main strengths
3. What could be improved

Keep it concise."""

            response = requests.post(
                f"{self.cloud_url}/api/generate",
                json={
                    "model": self.cloud_model,
                    "prompt": analysis_prompt,
                    "stream": False,
                    "options": {**CLOUD_CONFIG, "num_predict": 200}
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('response', '').strip()
                
                return {
                    "analysis": content,
                    "prompt": prompt
                }
                
        except Exception as e:
            logger.error(f"Prompt analysis failed: {e}")
            return {
                "analysis": "Analysis unavailable",
                "prompt": prompt
            }
