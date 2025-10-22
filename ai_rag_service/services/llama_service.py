import requests
import json
import os
from dotenv import load_dotenv
load_dotenv()

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL")
MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME")

GPU_CONFIG = {
    "num_gpu": int(os.getenv("OLLAMA_NUM_GPU")),        
    "num_thread": int(os.getenv("OLLAMA_NUM_THREAD")),   
    "num_ctx": int(os.getenv("OLLAMA_NUM_CTX")),       
    "temperature": float(os.getenv("OLLAMA_TEMPERATURE")),
    "top_p": float(os.getenv("OLLAMA_TOP_P")),
    "top_k": int(os.getenv("OLLAMA_TOP_K")),
    "repeat_penalty": float(os.getenv("OLLAMA_REPEAT_PENALTY")),
    "main_gpu": int(os.getenv("OLLAMA_MAIN_GPU")),
    "low_vram": os.getenv("OLLAMA_LOW_VRAM", "False").lower() == "true",
}

OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT"))

ENABLE_LLM_FALLBACK = os.getenv("ENABLE_LLM_FALLBACK", "True").lower() == "true"

print(f"✓ LLM Configuration loaded from .env:")
print(f"  - Model: {MODEL_NAME}")
print(f"  - API URL: {OLLAMA_API_URL}")
print(f"  - GPU Layers: {GPU_CONFIG['num_gpu']} (99 = all layers on GPU, 0 = CPU only)")
print(f"  - CPU Threads: {GPU_CONFIG['num_thread']}")
print(f"  - Temperature: {GPU_CONFIG['temperature']}")
print(f"  - Timeout: {OLLAMA_TIMEOUT}s")
print(f"  - Fallback Enabled: {ENABLE_LLM_FALLBACK}")
print(f"\n  Note: If GPU not available, Ollama will automatically use CPU.")
print(f"  To force CPU: Set OLLAMA_NUM_GPU=0 in .env") 

def generate_vendor_recommendation(prompt: str, vendor_data: list, min_similarity: float = None) -> dict:
    """
    Use LLaMA model to generate intelligent vendor recommendations.
    Returns a structured response with recommendations and reasoning.
    """
    
    # Use default from .env
    if min_similarity is None:
        min_similarity = float(os.getenv("MIN_SIMILARITY_THRESHOLD", "0.5"))
    """
    Use LLaMA model to generate intelligent vendor recommendations.
    Returns a structured response with recommendations and reasoning.
    """
    
    # Filter vendors by minimum similarity threshold
    relevant_vendors = [v for v in vendor_data if v.get('similarity', 0) >= min_similarity]
    
    # If no vendors meet the threshold, return a helpful message
    if not relevant_vendors:
        return {
            "status": "no_match",
            "message": "I couldn't find any vendors that closely match your requirements. Please provide more details about your event, such as:\n- Event type (e.g., wedding, birthday, corporate)\n- Specific services needed (e.g., decoration, catering, photography)\n- Location preferences\n- Budget range\n\nThis will help me find the most suitable vendors for you.",
            "vendors": []
        }
    
    # Limit to top 3 most similar vendors
    top_vendors = relevant_vendors[:3]
    
    vendor_context = []
    for i, vendor in enumerate(top_vendors, 1):
        vendor_info = f"""
Vendor {i}:
- Name: {vendor.get('vendorName', 'N/A')}
- Type: {vendor.get('vendorType', 'N/A')}
- Description: {vendor.get('description', 'N/A')}
- Location: {vendor.get('location', 'N/A')}
- Rating: {vendor.get('rating', 'N/A')}/5
- Tags: {', '.join(vendor.get('tags', []))}
- Pricing: {vendor.get('pricing', {}).get('currency', 'LKR')} {vendor.get('pricing', {}).get('averageCost', 'N/A')}
- Similarity Score: {vendor.get('similarity', 0):.2%}
"""
        vendor_context.append(vendor_info)
    
    # Create a detailed prompt for LLaMA
    llm_prompt = f"""You are an expert event planning assistant. A user has requested: "{prompt}"

Based on the user's request, I have found {len(top_vendors)} matching vendor(s). Please analyze each vendor and provide:
1. A brief explanation of why each vendor matches (or doesn't perfectly match) the user's needs
2. A ranking recommendation
3. Any important considerations

Here are the vendors:
{chr(10).join(vendor_context)}

Instructions:
- Be specific about how each vendor relates to the user's request
- If a vendor doesn't perfectly match, explain why and what aspects do match
- Keep each explanation concise (2-3 sentences)
- Rank them from most to least suitable
- If the user's request is vague or incomplete, mention what additional information would help

Provide your response in the following format:

**Overall Assessment:**
[Brief summary of how well these vendors match the request]

**Recommended Vendors (Ranked):**

1. [Vendor Name] - [Brief explanation of suitability and match to request]

2. [Vendor Name] - [Brief explanation of suitability and match to request]

3. [Vendor Name] - [Brief explanation of suitability and match to request]

**Additional Recommendations:**
[Any suggestions or considerations for the user]
"""
    
    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": MODEL_NAME,
                "prompt": llm_prompt,
                "stream": False,
                "options": GPU_CONFIG 
            },
            timeout=OLLAMA_TIMEOUT  
        )
        
        if response.status_code == 200:
            llm_response = response.json()
            recommendation_text = llm_response.get('response', '')
            
            return {
                "status": "success",
                "message": recommendation_text,
                "vendors": top_vendors
            }
        else:
            # Fallback if LLM fails
            if ENABLE_LLM_FALLBACK:
                return generate_fallback_recommendation(prompt, top_vendors)
            else:
                raise Exception(f"LLM request failed with status code: {response.status_code}")
            
    except Exception as e:
        print(f"Error calling LLaMA model: {str(e)}")
        if ENABLE_LLM_FALLBACK:
            return generate_fallback_recommendation(prompt, top_vendors)
        else:
            raise Exception(f"LLM service unavailable: {str(e)}")


def generate_fallback_recommendation(prompt: str, vendors: list) -> dict:
    """
    Fallback recommendation if LLM is unavailable.
    """
    vendor_list = []
    for i, vendor in enumerate(vendors, 1):
        vendor_list.append(
            f"{i}. {vendor.get('vendorName')} - {vendor.get('vendorType')} "
            f"(Rating: {vendor.get('rating', 'N/A')}/5, Match: {vendor.get('similarity', 0):.0%})"
        )
    
    message = f"""Based on your request: "{prompt}"

I found {len(vendors)} suitable vendor(s):

{chr(10).join(vendor_list)}

Note: The LLM service is currently unavailable. These recommendations are based on similarity matching.
"""
    
    return {
        "status": "success",
        "message": message,
        "vendors": vendors
    }
