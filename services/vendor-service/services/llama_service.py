import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Cloud-based Ollama configuration for RAG system
OLLAMA_CLOUD_URL = os.getenv("OLLAMA_CLOUD_URL", "https://ollama.ai/api")
CLOUD_MODEL_NAME = os.getenv("OLLAMA_CLOUD_MODEL", "glm-4.6:cloud")

# Fallback to local if needed
USE_LOCAL_FALLBACK = os.getenv("USE_LOCAL_OLLAMA_FALLBACK", "false").lower() == "true"
OLLAMA_LOCAL_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
LOCAL_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "llama3.2:3b")

# Cloud configuration (simplified - cloud handles optimization)
CLOUD_CONFIG = {
    "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
    "top_p": float(os.getenv("OLLAMA_TOP_P", "0.9")),
    "top_k": int(os.getenv("OLLAMA_TOP_K", "40")),
    "repeat_penalty": float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.1")),
    "num_predict": 200  # Limit for faster responses
}

OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "30"))
ENABLE_LLM_FALLBACK = os.getenv("ENABLE_LLM_FALLBACK", "true").lower() == "true"

print(f"✓ LLM Configuration for RAG System:")
print(f"  - Cloud Model: {CLOUD_MODEL_NAME} @ {OLLAMA_CLOUD_URL}")
if USE_LOCAL_FALLBACK:
    print(f"  - Local Fallback: {LOCAL_MODEL_NAME} @ {OLLAMA_LOCAL_URL}")
print(f"  - Temperature: {CLOUD_CONFIG['temperature']}")
print(f"  - Timeout: {OLLAMA_TIMEOUT}s")
print(f"  - Fallback Enabled: {ENABLE_LLM_FALLBACK}") 


def generate_vendor_recommendation(prompt: str, vendor_data: list, min_similarity: float = None) -> dict:
    """
    Use LLaMA model to generate intelligent vendor recommendations.
    Optimized for speed and accuracy.
    Returns a structured response with recommendations and reasoning.
    """
    
    # Use default from .env
    if min_similarity is None:
        min_similarity = float(os.getenv("MIN_SIMILARITY_THRESHOLD", "0.3"))
    
    # Filter vendors more intelligently
    relevant_vendors = [v for v in vendor_data if v.get('similarity', 0) >= min_similarity]
    
    # If no vendors meet the threshold, check if there's at least one decent match
    if not relevant_vendors and vendor_data:
        best_vendor = max(vendor_data, key=lambda x: x.get('similarity', 0))
        best_similarity = best_vendor.get('similarity', 0)
        
        if best_similarity >= 0.20:
            relevant_vendors = [best_vendor]
        else:
            return {
                "status": "no_match",
                "message": "I couldn't find vendors that match your specific requirements. Consider:\n- Adjusting your location preferences\n- Expanding your budget range\n- Being more flexible with service types\n- Checking if similar vendors are available in nearby areas",
                "vendors": []
            }
    
    # Apply smart filtering to remove low-similarity outliers
    if len(relevant_vendors) > 1:
        best_similarity = relevant_vendors[0].get('similarity', 0)
        
        filtered_vendors = []
        for vendor in relevant_vendors:
            vendor_similarity = vendor.get('similarity', 0)
            if vendor_similarity >= max(min_similarity, best_similarity * 0.5):
                filtered_vendors.append(vendor)
        
        relevant_vendors = filtered_vendors
    
    # Limit to maximum 3 vendors
    top_vendors = relevant_vendors[:3]
    
    # Build concise vendor context for faster LLM processing
    vendor_summaries = []
    for i, vendor in enumerate(top_vendors, 1):
        summary = (
            f"{i}. {vendor.get('vendorName')} ({vendor.get('vendorType')})\n"
            f"   - Services: {vendor.get('description', 'N/A')[:200]}...\n"
            f"   - Location: {vendor.get('location')}, Rating: {vendor.get('rating')}/5\n"
            f"   - Budget: {vendor.get('pricing', {}).get('currency', 'LKR')} {vendor.get('pricing', {}).get('averageCost', 'N/A')}\n"
            f"   - Match Score: {vendor.get('similarity', 0):.1%}"
        )
        vendor_summaries.append(summary)
    
    # Create optimized, concise prompt for faster LLM response
    llm_prompt = f"""You are an event planning AI assistant. Analyze these vendors for: "{prompt}"

Vendors found:
{chr(10).join(vendor_summaries)}

Provide a CONCISE response (max 150 words) with:
1. Quick assessment of match quality
2. Top recommendation with 1-2 key reasons
3. Brief mention of alternatives if applicable

Keep it brief, actionable, and user-friendly. Focus on the BEST match."""
    
    try:
        # Try cloud-based Ollama API first
        try:
            response = requests.post(
                f"{OLLAMA_CLOUD_URL}/api/generate",
                json={
                    "model": CLOUD_MODEL_NAME,
                    "prompt": llm_prompt,
                    "stream": False,
                    "options": CLOUD_CONFIG
                },
                timeout=OLLAMA_TIMEOUT
            )
            
            if response.status_code == 200:
                llm_response = response.json()
                recommendation_text = llm_response.get('response', '').strip()
                
                return {
                    "status": "success",
                    "message": recommendation_text,
                    "vendors": top_vendors,
                    "model_used": CLOUD_MODEL_NAME
                }
            else:
                print(f"⚠️ Cloud API returned {response.status_code}")
                raise Exception(f"Cloud API error: {response.status_code}")
        
        except Exception as cloud_error:
            print(f"⚠️ Cloud LLM failed: {str(cloud_error)}")
            
            # Try local fallback if enabled
            if USE_LOCAL_FALLBACK:
                print(f"🔄 Trying local Ollama fallback...")
                try:
                    local_response = requests.post(
                        f"{OLLAMA_LOCAL_URL}/api/generate",
                        json={
                            "model": LOCAL_MODEL_NAME,
                            "prompt": llm_prompt,
                            "stream": False,
                            "options": CLOUD_CONFIG
                        },
                        timeout=OLLAMA_TIMEOUT
                    )
                    
                    if local_response.status_code == 200:
                        llm_response = local_response.json()
                        recommendation_text = llm_response.get('response', '').strip()
                        
                        return {
                            "status": "success",
                            "message": recommendation_text,
                            "vendors": top_vendors,
                            "model_used": f"{LOCAL_MODEL_NAME} (local fallback)"
                        }
                except Exception as local_error:
                    print(f"❌ Local fallback also failed: {str(local_error)}")
            
            # Use default fallback
            if ENABLE_LLM_FALLBACK:
                return generate_fallback_recommendation(prompt, top_vendors)
            else:
                raise Exception(f"LLM service unavailable: {str(cloud_error)}")
            
    except requests.exceptions.Timeout:
        print(f"LLM request timed out - using fallback")
        if ENABLE_LLM_FALLBACK:
            return generate_fallback_recommendation(prompt, top_vendors)
        else:
            raise Exception("LLM service timeout")
    except Exception as e:
        print(f"Error calling LLM model: {str(e)}")
        if ENABLE_LLM_FALLBACK:
            return generate_fallback_recommendation(prompt, top_vendors)
        else:
            raise Exception(f"LLM service unavailable: {str(e)}")


def generate_fallback_recommendation(prompt: str, vendors: list) -> dict:
    """
    Fast fallback recommendation if LLM is unavailable.
    Provides structured, user-friendly response without LLM.
    """
    if not vendors:
        return {
            "status": "no_match",
            "message": "No suitable vendors found. Try adjusting your search criteria.",
            "vendors": []
        }
    
    # Get top vendor
    top_vendor = vendors[0]
    vendor_name = top_vendor.get('vendorName', 'N/A')
    similarity = top_vendor.get('similarity', 0)
    
    # Build recommendation message
    message_parts = [
        f"**Top Recommendation:** {vendor_name}",
        f"",
        f"This vendor matches your requirements with a {similarity:.0%} confidence score.",
        f"",
        f"**Why this vendor:**",
        f"- Specializes in {top_vendor.get('vendorType', 'event services')}",
        f"- Located in {top_vendor.get('location', 'your area')}",
        f"- Rated {top_vendor.get('rating', 'N/A')}/5",
        f"- Average cost: {top_vendor.get('pricing', {}).get('currency', 'LKR')} {top_vendor.get('pricing', {}).get('averageCost', 'N/A')}",
    ]
    
    # Add alternatives if available
    if len(vendors) > 1:
        message_parts.append("")
        message_parts.append(f"**Alternatives:** {len(vendors) - 1} other vendor(s) also available.")
    
    message = "\n".join(message_parts)
    
    return {
        "status": "success",
        "message": message,
        "vendors": vendors
    }
