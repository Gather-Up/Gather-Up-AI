"""
Test image service directly
"""
import requests
import json

print("Testing image service directly on port 8003...")
print()

try:
    response = requests.post(
        "http://localhost:8003/api/images/generate",
        json={"prompt": "a beautiful sunset over mountains"},
        timeout=120
    )

    print(f"Status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    print()
    
    if response.status_code == 200:
        print("✅ Success!")
        result = response.json()
        print(f"Image URL: {result.get('image_url', 'N/A')}")
        print(f"Metadata: {result.get('metadata', 'N/A')}")
    else:
        print("❌ Error:")
        try:
            error_data = response.json()
            print(json.dumps(error_data, indent=2))
        except:
            print(response.text)
except Exception as e:
    print(f"❌ Exception: {e}")
    import traceback
    traceback.print_exc()
