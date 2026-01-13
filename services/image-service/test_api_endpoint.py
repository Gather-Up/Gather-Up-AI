"""
Test the actual image generation endpoint
"""
import httpx
import asyncio
import json

async def test_generate_endpoint():
    url = "http://localhost:8003/api/images/generate"
    
    payload = {
        "prompt": "Create a stunning visual for an event: Help me plan a wedding for 200 guests in Kandy with full vendor recommendations. The event will feature services from: Royal (Decoration). Taking place at: Regan - Wedding Planner (point_of_interest). Create a photorealistic, high-quality image that captures the atmosphere and essence of this event.",
        "width": 1024,
        "height": 1024,
        "enhance_prompt": False,
        "upload_to_cloudinary": False
    }
    
    print("=" * 70)
    print("Testing Image Generation API")
    print("=" * 70)
    print(f"\nEndpoint: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("\nSending request...\n")
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, json=payload)
            
            print(f"Status Code: {response.status_code}")
            print(f"\nResponse:")
            print("=" * 70)
            
            if response.status_code == 200:
                result = response.json()
                print(json.dumps(result, indent=2)[:500])
                print("\n✅ SUCCESS!")
                
                if result.get("success"):
                    print(f"\nGeneration Time: {result.get('generation_time_seconds')}s")
                    print(f"Prompt ID: {result.get('prompt_id')}")
                    print(f"Seed: {result.get('seed')}")
                    
                    image_url = result.get('image_url', '')
                    if image_url.startswith('data:image'):
                        print(f"Image: base64 data ({len(image_url)} chars)")
                    else:
                        print(f"Image URL: {image_url}")
            else:
                print(response.text)
                print("\n❌ FAILED!")
                
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_generate_endpoint())
