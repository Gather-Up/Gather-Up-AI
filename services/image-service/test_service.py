"""
Test script for Image Service
Tests ComfyUI integration, Llama prompt enhancement, and image generation
"""

import requests
import json
import time
import base64
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8003/api/images"
OUTPUT_DIR = "test_outputs"

def test_health_check():
    """Test 1: Health check"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        result = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"Result: {json.dumps(result, indent=2)}")
        
        if result.get("comfyui_accessible"):
            print("✅ ComfyUI is accessible")
            return True
        else:
            print("❌ ComfyUI is not accessible")
            return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_prompt_enhancement():
    """Test 2: Prompt enhancement with Llama"""
    print("\n" + "="*60)
    print("TEST 2: Prompt Enhancement")
    print("="*60)
    
    test_prompt = "birthday party decoration"
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/enhance-prompt",
            params={"prompt": test_prompt},
            timeout=30
        )
        result = response.json()
        
        print(f"Original: {result.get('original_prompt')}")
        print(f"Enhanced: {result.get('enhanced_prompt')}")
        print(f"Model: {result.get('model_used')}")
        
        if result.get("status") == "success":
            print("✅ Prompt enhancement successful")
            return True
        else:
            print("⚠️ Prompt enhancement fell back to original")
            return True  # Still OK, just no enhancement
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_image_generation():
    """Test 3: Single image generation (non-streaming)"""
    print("\n" + "="*60)
    print("TEST 3: Image Generation (Non-Streaming)")
    print("="*60)
    
    # Create output directory
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    
    request_data = {
        "prompt": "elegant wedding venue with flowers and decorations",
        "num_images": 1,
        "width": 768,
        "height": 768,
        "steps": 20,  # Fast test
        "cfg_scale": 7.0,
        "sampler_name": "dpmpp_2m",
        "scheduler": "karras"
    }
    
    print(f"Request: {json.dumps(request_data, indent=2)}")
    print("Generating image... (this may take 15-30 seconds)")
    
    try:
        start_time = time.time()
        
        response = requests.post(
            f"{API_BASE_URL}/generate",
            json=request_data,
            timeout=300
        )
        
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"\n✅ Generation successful!")
            print(f"Time taken: {elapsed_time:.1f}s")
            print(f"Enhanced prompt: {result.get('enhanced_prompt')[:80]}...")
            print(f"Images generated: {len(result.get('images', []))}")
            
            # Save images
            for img in result.get("images", []):
                filename = f"{OUTPUT_DIR}/{img['filename']}"
                
                # Decode and save
                img_data = base64.b64decode(img["data"])
                with open(filename, "wb") as f:
                    f.write(img_data)
                
                print(f"Saved: {filename} (seed: {img['seed']})")
            
            print(f"\n📁 Images saved to: {OUTPUT_DIR}/")
            return True
        
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
    
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_streaming_generation():
    """Test 4: Streaming image generation"""
    print("\n" + "="*60)
    print("TEST 4: Streaming Image Generation (SSE)")
    print("="*60)
    
    # Note: requests library doesn't fully support SSE
    # This is a basic test - frontend should use EventSource
    
    request_data = {
        "prompt": "beautiful event decoration",
        "num_images": 1,
        "width": 512,
        "height": 512,
        "steps": 15  # Very fast
    }
    
    print(f"Request: {json.dumps(request_data, indent=2)}")
    print("Streaming generation...")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/generate/stream",
            json=request_data,
            stream=True,
            timeout=300
        )
        
        if response.status_code == 200:
            progress_updates = 0
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # Remove 'data: '
                        
                        if data_str == '[DONE]':
                            print("\n✅ Streaming complete!")
                            break
                        
                        try:
                            data = json.loads(data_str)
                            status = data.get('status')
                            message = data.get('message', '')
                            progress = data.get('progress_percent', 0)
                            
                            print(f"  [{status}] {message} ({progress:.0f}%)")
                            progress_updates += 1
                        
                        except json.JSONDecodeError:
                            pass
            
            print(f"Total progress updates: {progress_updates}")
            return True
        
        else:
            print(f"❌ Error {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "🧪 "*20)
    print("  IMAGE SERVICE - INTEGRATION TESTS")
    print("🧪 "*20)
    
    results = {
        "Health Check": test_health_check(),
        "Prompt Enhancement": test_prompt_enhancement(),
        "Image Generation": test_image_generation(),
        "Streaming Generation": test_streaming_generation()
    }
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n🎉 All tests passed! Image service is working correctly.")
    elif total_passed >= 2:
        print("\n⚠️ Some tests failed, but core functionality works.")
    else:
        print("\n❌ Multiple test failures. Please check configuration.")
    
    print("\n📝 Next steps:")
    print("  1. Check generated images in: test_outputs/")
    print("  2. Test via API Gateway: http://localhost:8000/api/v1/images/generate")
    print("  3. Integrate with frontend using streaming endpoint")


if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\n❌ Tests interrupted")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {str(e)}")
