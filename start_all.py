import subprocess
import os
import sys
from pathlib import Path
import time

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# Service configurations
SERVICES = [
    {
        "name": "API Gateway",
        "path": PROJECT_ROOT / "api-gateway",
        "command": "python main.py",
        "port": "8000"
    },
    {
        "name": "Vendor Service",
        "path": PROJECT_ROOT / "services" / "vendor-service",
        "command": "python main.py",
        "port": "8001"
    },
    {
        "name": "Location Service",
        "path": PROJECT_ROOT / "services" / "location-service",
        "command": "python main.py",
        "port": "8002"
    },
    {
        "name": "Image Service",
        "path": PROJECT_ROOT / "services" / "image-service",
        "command": "python main.py",
        "port": "8003"
    }
]

def find_venv():
    common_venv_names = ['venv', '.venv', 'env', '.env', 'virtualenv']
    
    for venv_name in common_venv_names:
        venv_path = PROJECT_ROOT / venv_name
        if venv_path.exists():
            return venv_path
    
    return None

def get_activation_command(venv_path):
    activate_script = venv_path / "Scripts" / "activate.bat"
    if activate_script.exists():
        return str(activate_script)
    return None

def start_service(service):
    """Start a service in a new PowerShell window"""
    venv_path = find_venv()
    
    if venv_path:
        activate_cmd = get_activation_command(venv_path)
        if activate_cmd:
            # Create a command that activates venv and runs the service
            full_command = f'cd "{service["path"]}" && call "{activate_cmd}" && {service["command"]}'
        else:
            print(f"Warning: Virtual environment found but activation script missing")
            full_command = f'cd "{service["path"]}" && {service["command"]}'
    else:
        print(f"Warning: No virtual environment found. Running without venv.")
        full_command = f'cd "{service["path"]}" && {service["command"]}'
    
    # Start in a new command prompt window
    cmd = f'start "GatherUp - {service["name"]}" cmd /k "{full_command}"'
    
    subprocess.Popen(cmd, shell=True)
    print(f"✅ Started {service['name']} on port {service['port']}")
    time.sleep(1)  # Small delay between starting services

def main():
    """Main launcher function"""
    print("=" * 60)
    print("🚀 GatherUp AI - Service Launcher")
    print("=" * 60)
    print()
    
    # Check for virtual environment
    venv_path = find_venv()
    if venv_path:
        print(f"✅ Found virtual environment: {venv_path.name}")
    else:
        print("⚠️  No virtual environment found!")
        print("   Looking for: venv, .venv, env, .env, virtualenv")
        response = input("\n   Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("❌ Startup cancelled")
            return
    
    print()
    print("Starting all services...")
    print("-" * 60)
    
    # Start all services
    for service in SERVICES:
        if service["path"].exists():
            start_service(service)
        else:
            print(f"⚠️  Warning: {service['name']} path not found: {service['path']}")
    
    print()
    print("=" * 60)
    print("✅ All services have been launched!")
    print("=" * 60)
    print()
    print("Service URLs:")
    print(f"  • API Gateway:      http://localhost:8000")
    print(f"  • Vendor Service:   http://localhost:8001")
    print(f"  • Location Service: http://localhost:8002")
    print(f"  • Image Service:    http://localhost:8003")
    print()
    print("⚠️  Important: Ensure ComfyUI is running on http://localhost:8188")
    print("   Image service requires ComfyUI to be active.")
    print()
    print("📝 Each service is running in a separate window.")
    print("   Close the windows to stop the services.")
    print()
    print("Press any key to exit this launcher...")
    input()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Launcher interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        input("Press any key to exit...")
