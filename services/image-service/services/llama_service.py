"""
Llama Service for Image Prompt Enhancement
Uses Llama 3.2 3B to enhance user prompts for better SDXL generation
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL")
MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "llama3.2:3b")

# Configuration for image prompt enhancement (faster, creative)
PROMPT_ENHANCEMENT_CONFIG = {
    "num_gpu": int(os.getenv("OLLAMA_NUM_GPU", "99")),
    "num_thread": int(os.getenv("OLLAMA_NUM_THREAD", "8")),
    "temperature": 0.8,  # More creative for image prompts
    "top_p": 0.9,
    "top_k": 40,
    "repeat_penalty": 1.1,
}

OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))

print(f"✓ Llama Service Configuration for Image Prompts:")
print(f"  - Model: {MODEL_NAME}")
print(f"  - API URL: {OLLAMA_API_URL}")
print(f"  - Temperature: {PROMPT_ENHANCEMENT_CONFIG['temperature']} (creative mode)")


def enhance_image_prompt(user_prompt: str, context: str = None) -> dict:
    """
    Enhance user's simple prompt into a detailed SDXL-optimized prompt
    
    Args:
        user_prompt: User's natural language description
        context: Optional context (e.g., event type, theme)
    
    Returns:
        dict with enhanced_prompt and analysis
    """
    
    # Build system instruction for Llama
    system_prompt = """You are an expert AI assistant specialized in creating detailed, high-quality prompts for Stable Diffusion XL image generation.

Your task: Transform simple user descriptions into detailed, effective SDXL prompts that produce stunning images.

RULES:
1. Keep the enhanced prompt under 75 words
2. Include specific visual details: lighting, composition, style, mood, colors
3. Add quality boosters: "highly detailed", "professional photography", "8k resolution"
4. Be descriptive but concise
5. Focus on what TO include, not what to avoid (negatives handled separately)
6. Use comma-separated descriptors
7. Maintain the core intent of the user's request

Example transformations:
- "birthday party decoration" → "elegant birthday party decoration setup, colorful balloons and streamers, beautiful cake centerpiece, warm ambient lighting, vibrant colors, professional event photography, highly detailed, 8k resolution"
- "wedding venue" → "luxurious wedding venue interior, elegant floral arrangements, romantic lighting, pristine white and gold decor, grand chandeliers, professional photography, cinematic composition, highly detailed, 8k"

Respond ONLY with the enhanced prompt. No explanations, no additional text."""
    
    # Build user message
    user_message = f"Enhance this prompt for SDXL: \"{user_prompt}\""
    if context:
        user_message += f"\nContext: {context}"
    
    try:
        # Call Ollama API
        payload = {
            "model": MODEL_NAME,
            "prompt": f"{system_prompt}\n\n{user_message}",
            "stream": False,
            "options": PROMPT_ENHANCEMENT_CONFIG
        }
        
        response = requests.post(
            f"{OLLAMA_API_URL}/api/generate",
            json=payload,
            timeout=OLLAMA_TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            enhanced_prompt = result.get("response", "").strip()
            
            # Clean up the response (remove any extra formatting)
            enhanced_prompt = enhanced_prompt.replace('"', '').strip()
            
            # If Llama added unwanted text, try to extract just the prompt
            if ":" in enhanced_prompt and len(enhanced_prompt) > 100:
                parts = enhanced_prompt.split(":", 1)
                if len(parts[1]) > 20:
                    enhanced_prompt = parts[1].strip()
            
            # Ensure we have something valid
            if len(enhanced_prompt) < 10:
                enhanced_prompt = user_prompt
            
            print(f"✓ Prompt enhanced by Llama 3.2")
            print(f"  Original: {user_prompt[:50]}...")
            print(f"  Enhanced: {enhanced_prompt[:80]}...")
            
            return {
                "status": "success",
                "original_prompt": user_prompt,
                "enhanced_prompt": enhanced_prompt,
                "model_used": MODEL_NAME
            }
        
        else:
            print(f"❌ Ollama API error: {response.status_code}")
            return {
                "status": "fallback",
                "original_prompt": user_prompt,
                "enhanced_prompt": user_prompt,  # Use original as fallback
                "error": f"API returned {response.status_code}"
            }
    
    except requests.exceptions.Timeout:
        print(f"⚠️ Ollama timeout - using original prompt")
        return {
            "status": "fallback",
            "original_prompt": user_prompt,
            "enhanced_prompt": user_prompt,
            "error": "Timeout"
        }
    
    except Exception as e:
        print(f"❌ Llama service error: {str(e)}")
        return {
            "status": "fallback",
            "original_prompt": user_prompt,
            "enhanced_prompt": user_prompt,
            "error": str(e)
        }


def analyze_prompt_for_negative(user_prompt: str) -> str:
    """
    Analyze the prompt and generate appropriate negative prompts
    Returns a string of negative prompts
    """
    
    base_negatives = [
        "blurry", "low quality", "distorted", "deformed", "ugly",
        "bad anatomy", "bad proportions", "watermark", "text", "logo",
        "signature", "out of frame", "cropped"
    ]
    
    # Add context-specific negatives based on prompt content
    prompt_lower = user_prompt.lower()
    
    if "people" in prompt_lower or "person" in prompt_lower or "crowd" in prompt_lower:
        base_negatives.extend([
            "extra limbs", "missing limbs", "disfigured face",
            "poorly drawn hands", "poorly drawn face"
        ])
    
    if "outdoor" in prompt_lower or "landscape" in prompt_lower or "venue" in prompt_lower:
        base_negatives.extend([
            "overexposed", "underexposed", "harsh shadows"
        ])
    
    if "food" in prompt_lower or "cake" in prompt_lower or "catering" in prompt_lower:
        base_negatives.extend([
            "unappetizing", "artificial looking", "plastic"
        ])
    
    return ", ".join(base_negatives)
