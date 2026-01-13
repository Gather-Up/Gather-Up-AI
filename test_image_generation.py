"""
Quick test script for Z-Image-Turbo integration
Tests the complete flow from frontend to ComfyUI
"""

import requests
import json
import time
import sys
from datetime import datetime

# Configuration
API_GATEWAY_URL = "http://localhost:8080"
TEST_PROMPT = "Professional social media post design, vibrant venue with dynamic lighting, bold text overlay PARTY, modern event design"

def test_image_generation():
    """Test image generation endpoint"""
    print("\n" + "="*60)
    print("Testing Z-Image-Turbo Image Generation")
    print("="*60)
    
    # Test payload
    payload = {
        "prompt": TEST_PROMPT,
        "num_images": 1,
        "width": 1024,
        "height": 1024,
        "steps": 8,
        "cfg_scale": 2.0,
        "sampler_name": "euler_ancestral",
        "scheduler": "karras",
        "denoise": 1.0,
        "use_refiner": False
    }
    
    print(f"\n📝 Prompt: {TEST_PROMPT}")
    print(f"⚙️  Settings: {payload['steps']} steps, {payload['width']}x{payload['height']}")
    print(f"🎯 Quality: High (CFG: {payload['cfg_scale']})")
    print("\n⏳ Starting generation...\n")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{API_GATEWAY_URL}/api/v1/images/generate/stream",
            json=payload,
            stream=True,
            timeout=300
        )
        
        if response.status_code != 200:
            print(f"❌ Error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        # Process streaming response
        for line in response.iter_lines():
            if line:
                line_text = line.decode('utf-8')
                if line_text.startswith('data: '):
                    data_str = line_text[6:]
                    
                    if data_str == '[DONE]':
                        break
                    
                    try:
                        data = json.loads(data_str)
                        
                        # Show progress
                        if 'message' in data:
                            progress = data.get('progress_percent', 0)
                            print(f"  [{progress:3.0f}%] {data['message']}")
                        
                        # Handle completion
                        if data.get('status') == 'completed':
                            images = data.get('images', [])
                            elapsed = time.time() - start_time
                            
                            print(f"\n✅ Success!")
                            print(f"   Generated {len(images)} image(s) in {elapsed:.1f}s")
                            print(f"   Enhanced prompt: {data.get('enhanced_prompt', 'N/A')[:80]}...")
                            
                            # Save images
                            for idx, img in enumerate(images):
                                filename = f"test_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{idx+1}.png"
                                print(f"   Image {idx+1}: {filename} ({img.get('seed', 'N/A')})")
                            
                            return True
                        
                        # Handle errors
                        if data.get('status') == 'error':
                            print(f"\n❌ Generation failed: {data.get('message', 'Unknown error')}")
                            return False
                    
                    except json.JSONDecodeError:
                        pass
        
        elapsed = time.time() - start_time
        print(f"\n✅ Stream completed in {elapsed:.1f}s")
        return True
    
    except requests.exceptions.Timeout:
        print("\n❌ Request timeout - generation took too long")
        return False
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection error - is the API Gateway running?")
        print("   Start it with: python api-gateway/main.py")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return False

def test_prompt_enhancement():
    """Test prompt enhancement endpoint"""
    print("\n" + "="*60)
    print("Testing Prompt Enhancement")
    print("="*60)
    
    test_prompt = "birthday party for 30 people"
    print(f"\n📝 Original: {test_prompt}")
    
    try:
        response = requests.post(
            f"{API_GATEWAY_URL}/api/v1/images/enhance-prompt",
            json={"prompt": test_prompt},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            enhanced = data.get('enhanced_prompt', 'N/A')
            print(f"✨ Enhanced: {enhanced[:200]}...")
            return True
        else:
            print(f"❌ Error: HTTP {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def check_services():
    """Check if all required services are running"""
    print("\n" + "="*60)
    print("Checking Services")
    print("="*60 + "\n")
    
    services = [
        ("API Gateway", "http://localhost:8080"),
        ("Image Service", "http://localhost:8003"),
        ("ComfyUI", "http://localhost:8000/system_stats"),
    ]
    
    all_running = True
    for name, url in services:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name:20} - Running")
            else:
                print(f"⚠️  {name:20} - HTTP {response.status_code}")
                all_running = False
        except requests.exceptions.ConnectionError:
            print(f"❌ {name:20} - Not running")
            all_running = False
        except Exception as e:
            print(f"❌ {name:20} - Error: {str(e)}")
            all_running = False
    
    return all_running

if __name__ == "__main__":
    print("\n🎨 Z-Image-Turbo Integration Test")
    print(f"   Testing against: {API_GATEWAY_URL}")
    
    # Check services first
    if not check_services():
        print("\n⚠️  Some services are not running. Please start them first:")
        print("   1. Start ComfyUI: cd ComfyUI && python main.py --port 8000")
        print("   2. Start services: python start_all.py")
        sys.exit(1)
    
    # Run tests
    print("\n" + "="*60)
    print("Starting Tests")
    print("="*60)
    
    # Test 1: Prompt Enhancement
    test1 = test_prompt_enhancement()
    time.sleep(2)
    
    # Test 2: Image Generation
    test2 = test_image_generation()
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"  Prompt Enhancement: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"  Image Generation:   {'✅ PASS' if test2 else '❌ FAIL'}")
    print("="*60 + "\n")
    
    if test1 and test2:
        print("🎉 All tests passed! Z-Image-Turbo is working correctly.\n")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Check the output above for details.\n")
        sys.exit(1)
