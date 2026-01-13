"""
Test image generation end-to-end
"""
import asyncio
import sys
from pathlib import Path
import httpx

async def test_generate():
    """Test the image generation endpoint"""
    
    print("=" * 60)
    print("Testing Image Generation")
    print("=" * 60)
    
    # Test data
    payload = {
        "prompt": "birthday party decorations with balloons",
        "enhance_prompt": True,
        "event_context": {
            "theme": "Birthday Party",
            "color_scheme": "pink and gold",
            "mood": "festive"
        },
        "width": 512,
        "height": 512
    }
    
    print(f"\n📝 Request:")
    print(f"   Prompt: {payload['prompt']}")
    print(f"   Size: {payload['width']}x{payload['height']}")
    print(f"   Theme: {payload['event_context']['theme']}")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print("\n⏳ Sending request to image service...")
            response = await client.post(
                "http://localhost:8003/api/images/generate",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                print("\n✅ Image generated successfully!")
                print(f"\n📸 Result:")
                print(f"   Image URL: {result.get('image_url', 'N/A')}")
                print(f"   Enhanced Prompt: {result.get('enhanced_prompt', 'N/A')[:100]}...")
                print(f"   Model: {result.get('metadata', {}).get('model', 'N/A')}")
                print(f"   Generation Time: {result.get('metadata', {}).get('generation_time', 'N/A')}s")
            else:
                print(f"\n❌ Request failed: {response.status_code}")
                print(f"   Error: {response.text}")
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_generate())
