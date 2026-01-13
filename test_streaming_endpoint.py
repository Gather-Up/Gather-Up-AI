"""
Test the streaming endpoint to verify SSE format
"""
import httpx
import asyncio

async def test_streaming():
    url = "http://localhost:8080/api/v1/images/generate/stream"
    
    payload = {
        "prompt": "A beautiful wedding venue in Kandy with elegant decorations",
        "width": 1024,
        "height": 1024,
        "enhance_prompt": False,
        "upload_to_cloudinary": False
    }
    
    print("=" * 70)
    print("Testing Streaming Image Generation")
    print("=" * 70)
    print(f"\nEndpoint: {url}")
    print(f"Prompt: {payload['prompt']}\n")
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                print(f"Status Code: {response.status_code}")
                print(f"Content-Type: {response.headers.get('content-type')}\n")
                
                if response.status_code != 200:
                    text = await response.aread()
                    print(f"Error: {text.decode()}")
                    return
                
                print("Streaming events:\n")
                print("-" * 70)
                
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        
                        if data == '[DONE]':
                            print("\n✅ Stream completed!")
                            break
                        
                        try:
                            import json
                            parsed = json.loads(data)
                            
                            # Pretty print progress
                            if 'message' in parsed:
                                progress = parsed.get('progress_percent', 0)
                                print(f"[{progress:3d}%] {parsed['message']}")
                            
                            # Check for completion
                            if parsed.get('status') == 'completed':
                                print(f"\n🎉 Generation complete!")
                                if 'images' in parsed:
                                    print(f"   Images: {len(parsed['images'])} image(s)")
                                    for i, img in enumerate(parsed['images']):
                                        data_len = len(img.get('data', ''))
                                        print(f"   Image {i+1}: {img.get('format', 'unknown')} format, {data_len} chars base64")
                                
                                if 'metadata' in parsed:
                                    meta = parsed['metadata']
                                    print(f"   Metadata:")
                                    print(f"     - Prompt ID: {meta.get('prompt_id')}")
                                    print(f"     - Seed: {meta.get('seed')}")
                                    print(f"     - Generation time: {meta.get('generation_time_seconds')}s")
                            
                            # Check for errors
                            if parsed.get('status') == 'error':
                                print(f"\n❌ Error: {parsed.get('message', 'Unknown error')}")
                                break
                                
                        except json.JSONDecodeError:
                            print(f"Non-JSON line: {data}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_streaming())
