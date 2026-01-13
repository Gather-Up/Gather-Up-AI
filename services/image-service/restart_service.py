"""
Restart just the image service
"""
import subprocess
import sys
import os
from pathlib import Path

# Get the service directory
service_dir = Path(__file__).parent

# Check for virtual environment
venv_python = service_dir.parent.parent / ".venv" / "Scripts" / "python.exe"

if not venv_python.exists():
    print("❌ Virtual environment not found!")
    sys.exit(1)

print("🔄 Restarting Image Service...")
print("="*70)

# Start the service
cmd = [str(venv_python), "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003", "--reload"]

print(f"Running: {' '.join(cmd)}")
print()

os.chdir(service_dir)
subprocess.run(cmd)
