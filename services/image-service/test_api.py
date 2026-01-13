"""
Test the Z-Image Turbo service through the API
"""
import requests
import json

print("Testing Z-Image Turbo through the API Gateway...")
print("=" * 70)

# Test 1: Generate image
print("\n1. Generating image with Z-Image Turbo...")
payload = {
    "prompt": "a beautiful sunset over mountains, vibrant colors, high quality"
}

try:
    response = requests.post(
        "http://localhost:8080/api/v1/images/generate",
        json=payload,
        timeout=60
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Image generated successfully!")
        print(f"   Image URL: {result['image_url']}")
        print(f"   Prompt ID: {result['metadata']['prompt_id']}")
        print(f"   Size: {len(response.content)} bytes")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
except requests.exceptions.Timeout:
    print("❌ Request timed out")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Check service health
print("\n2. Checking image service health...")
try:
    response = requests.get("http://localhost:8003/health")
    if response.status_code == 200:
        health = response.json()
        print("✅ Service is healthy!")
        print(f"   Status: {health['status']}")
        print(f"   Services: {json.dumps(health['services'], indent=4)}")
    else:
        print(f"❌ Error: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 70)
print("✅ Tests complete!")
