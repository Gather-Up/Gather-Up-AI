"""
Test script for Image Service
Run this to verify your setup is working correctly
"""

import asyncio
import httpx
import json

# Configuration
IMAGE_SERVICE_URL = "http://localhost:8003"
API_GATEWAY_URL = "http://localhost:8080"

async def test_health():
    """Test health check endpoint"""
    print("=" * 50)
    print("Testing Health Check...")
    print("=" * 50)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{IMAGE_SERVICE_URL}/api/images/health")
            result = response.json()
            
            print(f"\nStatus: {result['status']}")
            print(f"ComfyUI Connected: {result['comfyui_connected']}")
            print(f"Ollama Connected: {result['ollama_connected']}")
            
            if result['available_models']:
                print("\nAvailable Models:")
                for model_type, models in result['available_models'].items():
                    print(f"  {model_type}: {len(models)} models")
            
            return result['status'] == 'healthy'
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

async def test_prompt_enhancement():
    """Test prompt enhancement"""
    print("\n" + "=" * 50)
    print("Testing Prompt Enhancement...")
    print("=" * 50)
    
    try:
        test_prompt = "birthday party for a 5 year old"
        
        print(f"\nOriginal Prompt: {test_prompt}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{IMAGE_SERVICE_URL}/api/images/enhance-prompt",
                json={
                    "prompt": test_prompt,
                    "event_context": {
                        "event_type": "birthday",
                        "theme": "superhero",
                        "color_scheme": "red and blue"
                    }
                }
            )
            result = response.json()
            
            print(f"\nEnhanced Prompt:")
            print(f"  {result['enhanced_prompt'][:200]}...")
            
            return True
    except Exception as e:
        print(f"❌ Prompt enhancement failed: {e}")
        return False

async def test_image_generation():
    """Test image generation"""
    print("\n" + "=" * 50)
    print("Testing Image Generation...")
    print("=" * 50)
    print("\n⚠️  This will take 10-15 seconds...")
    
    try:
        test_prompt = "colorful birthday party invitation"
        
        print(f"\nGenerating image for: {test_prompt}")
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{IMAGE_SERVICE_URL}/api/images/generate",
                json={
                    "prompt": test_prompt,
                    "enhance_prompt": True,
                    "event_context": {
                        "event_type": "birthday",
                        "theme": "fun and colorful"
                    },
                    "width": 1024,
                    "height": 1024,
                    "upload_to_cloudinary": False  # Skip Cloudinary for test
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"\n✅ Image generated successfully!")
                print(f"  Generation time: {result['generation_time_seconds']}s")
                print(f"  Seed: {result['seed']}")
                print(f"  Size: {result['width']}x{result['height']}")
                
                if result.get('enhanced_prompt'):
                    print(f"\n  Enhanced prompt used:")
                    print(f"    {result['enhanced_prompt'][:150]}...")
                
                if result.get('image_url'):
                    if result['image_url'].startswith('data:'):
                        print(f"\n  Image returned as base64 (no Cloudinary)")
                    else:
                        print(f"\n  Image URL: {result['image_url']}")
                
                return True
            else:
                print(f"❌ Generation failed: {response.status_code}")
                print(f"   {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Image generation failed: {e}")
        return False

async def test_via_gateway():
    """Test through API Gateway"""
    print("\n" + "=" * 50)
    print("Testing via API Gateway...")
    print("=" * 50)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test gateway health
            response = await client.get(f"{API_GATEWAY_URL}/health")
            
            if response.status_code == 200:
                print("\n✅ API Gateway is responding")
                
                # Test image service health through gateway
                response = await client.get(f"{API_GATEWAY_URL}/api/v1/images/health")
                result = response.json()
                
                print(f"\nImage Service Status via Gateway:")
                print(f"  Status: {result['status']}")
                print(f"  ComfyUI: {result['comfyui_connected']}")
                print(f"  Ollama: {result['ollama_connected']}")
                
                return True
            else:
                print(f"❌ Gateway health check failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Gateway test failed: {e}")
        print("   Make sure API Gateway is running on port 8080")
        return False

async def main():
    print("\n" + "=" * 50)
    print("🎨 GatherUp AI - Image Service Test Suite")
    print("=" * 50)
    
    results = []
    
    # Test 1: Health Check
    result = await test_health()
    results.append(("Health Check", result))
    
    if not result:
        print("\n❌ Health check failed. Please ensure:")
        print("   1. Image Service is running (python main.py)")
        print("   2. ComfyUI is running (http://127.0.0.1:8000)")
        print("   3. Ollama is running (http://localhost:11434)")
        return
    
    # Test 2: Prompt Enhancement
    result = await test_prompt_enhancement()
    results.append(("Prompt Enhancement", result))
    
    # Test 3: Image Generation
    print("\n📸 Would you like to test image generation?")
    print("   This will generate an actual image (takes ~10-15 seconds)")
    choice = input("   Run image generation test? (y/n): ").lower()
    
    if choice == 'y':
        result = await test_image_generation()
        results.append(("Image Generation", result))
    
    # Test 4: API Gateway Integration
    print("\n🌐 Would you like to test API Gateway integration?")
    choice = input("   Test via gateway? (y/n): ").lower()
    
    if choice == 'y':
        result = await test_via_gateway()
        results.append(("Gateway Integration", result))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your image service is ready to use!")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
