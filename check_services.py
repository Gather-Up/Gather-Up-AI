"""
Quick check to verify all services are running on correct ports
"""
import socket
import time

def check_port(port, service_name):
    """Check if a port is in use"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    
    if result == 0:
        print(f"✅ {service_name:20} - Running on port {port}")
        return True
    else:
        print(f"❌ {service_name:20} - NOT running on port {port}")
        return False

print("\n" + "="*60)
print("Checking GatherUp AI Services")
print("="*60 + "\n")

services = [
    (8000, "ComfyUI"),
    (8080, "API Gateway"),
    (8001, "Vendor Service"),
    (8002, "Location Service"),
    (8003, "Image Service"),
]

all_running = True
for port, name in services:
    if not check_port(port, name):
        all_running = False
    time.sleep(0.1)

print("\n" + "="*60)
if all_running:
    print("✅ All services are running correctly!")
else:
    print("⚠️  Some services are not running")
    print("\nTo start services:")
    print("  1. Start ComfyUI: cd ComfyUI && python main.py --port 8000")
    print("  2. Start GatherUp services: python start_all.py")
print("="*60 + "\n")
