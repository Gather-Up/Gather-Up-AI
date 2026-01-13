"""
Startup checker - verifies ComfyUI is running before starting image service
"""
import requests
import sys
import time

print("="*70)
print("Checking Prerequisites for Image Service")
print("="*70)
print()

# Check ComfyUI
print("1. Checking ComfyUI on http://127.0.0.1:8000...")
try:
    response = requests.get("http://127.0.0.1:8000/system_stats", timeout=3)
    if response.status_code == 200:
        print("   ✅ ComfyUI is running")
        print()
        print("✅ ALL CHECKS PASSED! You can now start the image service.")
        print()
        print("To start image service:")
        print("  cd services/image-service")
        print("  ../../.venv/Scripts/python.exe -m uvicorn main:app --reload --port 8003")
        sys.exit(0)
    else:
        print(f"   ❌ ComfyUI returned status {response.status_code}")
except Exception as e:
    print(f"   ❌ Cannot connect to ComfyUI: {e}")
    print()
    print("=" * 70)
    print("⚠️  ComfyUI is NOT running!")
    print("="*70)
    print()
    print("Please start ComfyUI first:")
    print("  1. Open ComfyUI Desktop application, OR")
    print("  2. Run: python D:/ComfyUI/main.py --listen 127.0.0.1 --port 8000")
    print()
    sys.exit(1)
