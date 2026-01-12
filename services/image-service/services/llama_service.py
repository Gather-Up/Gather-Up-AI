"""
Llama Service for Image Prompt Enhancement
Uses local Ollama API for prompt enhancement
"""

import requests
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()

# Local Ollama configuration (primary)
OLLAMA_LOCAL_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
LOCAL_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "llama3.2:3b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))

# Configuration for image prompt enhancement (creative)
PROMPT_ENHANCEMENT_CONFIG = {
    "temperature": 0.8,
    "top_p": 0.9,
    "top_k": 40,
    "repeat_penalty": 1.1,
    "num_predict": 300
}

print(f"✓ Llama Service Configuration for Image Prompts:")
print(f"  - Local Model: {LOCAL_MODEL_NAME} @ {OLLAMA_LOCAL_URL}")
print(f"  - Temperature: {PROMPT_ENHANCEMENT_CONFIG['temperature']} (creative mode)")


def enhance_image_prompt(user_prompt: str, context: str = None) -> dict:
    """
    Enhance user's prompt into a social media graphic prompt with text overlays
    Creates prompts for images that look like professional Instagram/Facebook posts
    
    Args:
        user_prompt: User's natural language description
        context: Optional context (e.g., event type, theme)
    
    Returns:
        dict with enhanced_prompt and analysis
    """
    
    # Build comprehensive system instruction for social media graphic generation
    system_prompt = """You are an expert in creating prompts for AI image generation to produce SOCIAL MEDIA EVENT GRAPHICS with text overlays.

YOUR TASK:
Analyze the user's event request and create a visual prompt that captures the essence of that specific event type.

CORE PRINCIPLES:

1. UNDERSTAND THE EVENT FIRST:
   - What type of event is this? (use your knowledge of all event types)
   - What's the typical visual style for this event?
   - What atmosphere/mood should it convey?
   - What colors and aesthetics match this event?

2. CREATE APPROPRIATE TEXT OVERLAYS:
   - Main text: Event type or name (SHORT, BOLD, IMPACTFUL)
   - Subtitle: Generic call-to-action or descriptor
   - Location: If mentioned in request
   - Examples:
     * Art Exhibition → "ART GALLERY" + "OPENING NIGHT"
     * Charity Gala → "CHARITY GALA" + "MAKE A DIFFERENCE"
     * Music Festival → "MUSIC FEST" + "LIVE PERFORMANCES"
     * Product Launch → "NEW LAUNCH" + "BE THE FIRST"
     * Sports Event → "CHAMPIONSHIP" + "JOIN THE ACTION"
   
3. VISUAL ELEMENTS TO INCLUDE:
   - Background: Setting/venue that matches the event type
   - Lighting: Appropriate to the event mood
   - Colors: Match the event's typical aesthetic
   - Font style: Match the event's personality (elegant, bold, playful, corporate, etc.)
   - Composition: Professional social media post design

4. USE YOUR KNOWLEDGE:
   - You know thousands of event types (not just weddings/conferences)
   - Apply appropriate visual styles for each
   - Think about what makes each event unique
   - Consider cultural and contextual appropriateness

5. NEVER INCLUDE:
   - Specific guest counts, dates, times
   - Phone numbers or contact details
   - Detailed pricing information
   - Personal names (unless it's a famous venue/location)

6. OUTPUT STRUCTURE:
   "Professional social media post design, [VENUE/SETTING appropriate to event], bold text overlay '[EVENT TYPE]' in [font style matching event], subtitle '[GENERIC CTA]', [color scheme and mood], [additional visual elements], Instagram-ready graphic design, high resolution"

EXAMPLES:

User: "charity fundraiser dinner"
Output: "Professional social media post design, elegant banquet hall with warm lighting, bold text overlay 'CHARITY GALA' in refined serif font, subtitle 'MAKE A DIFFERENCE', gold and burgundy color scheme, formal dining setup, sophisticated atmosphere, Instagram-ready composition"

User: "kids birthday party"
Output: "Professional social media post design, colorful party venue with balloons and decorations, bold text overlay 'BIRTHDAY PARTY' in playful rounded font, subtitle 'LET'S CELEBRATE', bright rainbow colors, fun energetic atmosphere, Instagram-ready design"

User: "startup pitch competition"
Output: "Professional social media post design, modern auditorium with stage lighting, bold text overlay 'PITCH COMPETITION' in contemporary sans-serif, subtitle 'INNOVATE & WIN', electric blue and white colors, dynamic tech atmosphere, Instagram-ready graphic"

REMEMBER: Be creative and contextually appropriate for ANY event type!"""
    
    # Build user message
    user_message = f"""User's event request: "{user_prompt}"

Analyze this event and create a professional social media graphic prompt:
1. Identify the event type (use your knowledge - it could be anything!)
2. Determine appropriate visual style, colors, and mood
3. Create fitting text overlays (event type + generic CTA)
4. Describe the venue/setting that matches this event
5. Specify font style that fits the event's personality

OUTPUT: Only the image generation prompt (50-80 words)"""
    
    if context:
        user_message += f"\nAdditional context: {context}"
    
    try:
        # Use local Ollama API
        payload = {
            "model": LOCAL_MODEL_NAME,
            "prompt": f"{system_prompt}\n\n{user_message}",
            "stream": False,
            "options": PROMPT_ENHANCEMENT_CONFIG
        }
        
        print(f"🚀 Calling local Ollama at {OLLAMA_LOCAL_URL}...")
        
        response = requests.post(
            f"{OLLAMA_LOCAL_URL}/api/generate",
            json=payload,
            timeout=OLLAMA_TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            enhanced_prompt = result.get("response", "").strip()
            
            print(f"✓ Local Ollama response: {enhanced_prompt[:150]}...")
            
            # Clean up response
            enhanced_prompt = enhanced_prompt.replace('"', '').strip()
            
            if "\n\nThis " in enhanced_prompt or "\n\nNote:" in enhanced_prompt:
                enhanced_prompt = enhanced_prompt.split("\n\n")[0].strip()
            
            meta_markers = ["OUTPUT:", "PROMPT:", "ENHANCED PROMPT:"]
            for marker in meta_markers:
                if enhanced_prompt.upper().startswith(marker):
                    enhanced_prompt = enhanced_prompt[len(marker):].strip()
                    break
            
            if 20 <= len(enhanced_prompt) <= 600:
                print(f"✓ Using local Ollama prompt ({len(enhanced_prompt)} chars)")
                print(f"  Design prompt: {enhanced_prompt[:120]}...")
                return {
                    "status": "success",
                    "original_prompt": user_prompt,
                    "enhanced_prompt": enhanced_prompt,
                    "model_used": LOCAL_MODEL_NAME
                }
            else:
                print(f"⚠️ Prompt length unusual ({len(enhanced_prompt)} chars), using fallback")
                raise ValueError("Invalid prompt length")
        else:
            print(f"❌ Local Ollama returned {response.status_code}")
            raise Exception(f"Ollama API error: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Ollama failed: {str(e)}")
        print(f"🛑 Using safe default prompt")
        fallback_prompt = create_safe_default_prompt(user_prompt)
            return {
                "status": "fallback",
                "original_prompt": user_prompt,
                "enhanced_prompt": fallback_prompt,
                "model_used": "default",
                "error": str(cloud_error)
            }
    
    except Exception as e:
        print(f"❌ Error enhancing prompt: {str(e)}")
        fallback_prompt = create_safe_default_prompt(user_prompt)
        return {
            "status": "fallback",
            "original_prompt": user_prompt,
            "enhanced_prompt": fallback_prompt,
            "error": str(e)
        }


def create_safe_default_prompt(user_prompt: str) -> str:
    """
    Create a flexible, intelligent default prompt for any event type
    Uses common sense and keywords to understand the event
    """
    
    prompt_lower = user_prompt.lower()
    
    # Initialize with neutral defaults
    text_content = "EVENT"
    subtitle = "JOIN US"
    setting = "modern event venue with professional lighting"
    font_style = "contemporary sans-serif font"
    colors = "balanced professional colors"
    
    # Smart detection for various event types
    event_keywords = {
        'wedding': ('WEDDING', 'SAVE THE DATE', 'elegant venue with floral decorations, romantic lighting', 'elegant serif', 'soft gold and white'),
        'hackathon': ('HACKATHON', 'INNOVATE', 'modern tech workspace with computers', 'bold modern sans-serif', 'vibrant blue and purple'),
        'birthday': ('CELEBRATION', 'PARTY TIME', 'colorful party venue with decorations', 'playful bold', 'bright festive colors'),
        'conference': ('CONFERENCE', 'REGISTER NOW', 'professional conference hall with stage', 'clean corporate', 'professional navy'),
        'concert': ('CONCERT', 'LIVE SHOW', 'dynamic stage with lighting effects', 'bold edgy', 'electric purple and black'),
        'festival': ('FESTIVAL', 'CELEBRATE', 'outdoor venue with festive atmosphere', 'vibrant bold', 'rainbow bright colors'),
        'seminar': ('SEMINAR', 'LEARN MORE', 'modern training room with presentation', 'clean professional', 'corporate blue and white'),
        'workshop': ('WORKSHOP', 'HANDS-ON', 'creative studio space with work areas', 'friendly modern', 'warm orange and grey'),
        'gala': ('GALA', 'EXCLUSIVE EVENT', 'luxurious ballroom with chandeliers', 'elegant sophisticated', 'gold and black'),
        'fundraiser': ('FUNDRAISER', 'SUPPORT', 'elegant venue with warm ambiance', 'refined serif', 'charity blue and gold'),
        'exhibition': ('EXHIBITION', 'EXPLORE', 'gallery space with art displays', 'minimal modern', 'clean white and accent'),
        'launch': ('LAUNCH', 'BE FIRST', 'sleek modern space with spotlights', 'bold contemporary', 'brand-forward colors'),
        'networking': ('NETWORKING', 'CONNECT', 'professional lounge with standing areas', 'clean business', 'professional grey and blue'),
        'party': ('PARTY', 'LET\'S CELEBRATE', 'vibrant venue with dynamic lighting', 'fun bold', 'energetic mixed colors'),
        'graduation': ('GRADUATION', 'CELEBRATE SUCCESS', 'auditorium with ceremonial setup', 'classic elegant', 'academic navy and gold'),
        'sports': ('TOURNAMENT', 'GAME ON', 'sports venue with team colors', 'athletic bold', 'dynamic team colors'),
        'charity': ('CHARITY EVENT', 'MAKE A DIFFERENCE', 'elegant venue with warm atmosphere', 'compassionate serif', 'warm caring colors'),
        'art': ('ART SHOW', 'OPENING NIGHT', 'gallery with artistic lighting', 'artistic modern', 'creative color palette'),
        'music': ('MUSIC EVENT', 'LIVE PERFORMANCE', 'stage with concert lighting', 'bold music', 'vibrant concert colors'),
        'food': ('FOOD FESTIVAL', 'TASTE & ENJOY', 'culinary venue with appetizing setup', 'friendly inviting', 'warm appetizing colors'),
    }
    
    # Check for keyword matches
    for keyword, (text, sub, set, font, col) in event_keywords.items():
        if keyword in prompt_lower:
            text_content, subtitle, setting, font_style, colors = text, sub, set, font, col
            break
    
    # Extract location if mentioned
    location_text = ""
    if "colombo" in prompt_lower:
        location_text = ", text 'COLOMBO' included"
    elif "kandy" in prompt_lower:
        location_text = ", text 'KANDY' included"
    
    # Build intelligent default prompt
    default_prompt = (
        f"Professional social media post design, {setting}, "
        f"bold text overlay '{text_content}' in large {font_style}, "
        f"subtitle '{subtitle}' in elegant text{location_text}, "
        f"{colors}, Instagram-ready graphic design, high resolution, "
        f"balanced composition with impactful visual hierarchy"
    )
    
    return default_prompt


def analyze_prompt_for_negative(user_prompt: str) -> str:
    """
    Analyze the prompt and generate appropriate negative prompts
    Returns a string of negative prompts
    """
    
    base_negatives = [
        "blurry", "low quality", "distorted", "deformed", "ugly",
        "bad anatomy", "bad proportions", "watermark", "signature",
        "out of frame", "cropped"
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
