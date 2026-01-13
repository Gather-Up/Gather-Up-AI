"""
Start all GatherUp AI services including Image Service
"""
import subprocess
import os
import sys
from pathlib import Path
import time

PROJECT_ROOT = Path(__file__).parent.absolute()

print("=" * 70)
print("🚀 Starting GatherUp AI Services")
print("=" * 70)
print()

# Check if ComfyUI is running
print("Checking ComfyUI...")
import requests
try:
    response = requests.get("http://127.0.0.1:8000/system_stats", timeout=2)
    if response.status_code == 200:
        print("✅ ComfyUI is running on http://127.0.0.1:8000")
    else:
        print("⚠️  ComfyUI responded but may have issues")
except:
    print("❌ ComfyUI is NOT running!")
    print("   Please start ComfyUI before running the services")
    print("   It should be available at: http://127.0.0.1:8000")
    input("\nPress Enter to continue anyway or Ctrl+C to exit...")

print()

# Services to start
services = [
    ("API Gateway", PROJECT_ROOT / "api-gateway", 8080),
    ("Vendor Service", PROJECT_ROOT / "services" / "vendor-service", 8001),
    ("Location Service", PROJECT_ROOT / "services" / "location-service", 8002),
    ("Image Service", PROJECT_ROOT / "services" / "image-service", 8003),
]

print("Starting services...")
print("-" * 70)

processes = []

for name, path, port in services:
    if not path.exists():
        print(f"⚠️  {name} path not found: {path}")
        continue
    
    venv_activate = path / "venv" / "Scripts" / "activate.bat"
    
    if venv_activate.exists():
        cmd = f'cd /d "{path}" && call "{venv_activate}" && python main.py'
    else:
        cmd = f'cd /d "{path}" && python main.py'
    
    # Start in new window
    proc = subprocess.Popen(
        f'start "GatherUp - {name}" cmd /k "{cmd}"',
        shell=True
    )
    processes.append((name, proc))
    print(f"✅ Started {name} on port {port}")
    time.sleep(1)

print()
print("=" * 70)
print("✅ All services launched!")
print("=" * 70)
print()
print("Service URLs:")
print(f"  • API Gateway:      http://localhost:8080")
print(f"  • Vendor Service:   http://localhost:8001")
print(f"  • Location Service: http://localhost:8002")
print(f"  • Image Service:    http://localhost:8003")
print()
print("📝 Each service is running in a separate window.")
print("   Close the windows to stop the services.")
print()
print("Press Enter to exit this launcher...")
input()
