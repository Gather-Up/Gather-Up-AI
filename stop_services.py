"""
Stop all GatherUp AI services running on specific ports
"""
import subprocess
import sys

print("\n" + "="*60)
print("Stopping GatherUp AI Services")
print("="*60 + "\n")

# Ports used by services
ports = {
    8080: "API Gateway",
    8001: "Vendor Service", 
    8002: "Location Service",
    8003: "Image Service"
}

stopped = 0
for port, name in ports.items():
    print(f"Checking port {port} ({name})...")
    
    # Find process using the port
    try:
        result = subprocess.run(
            f'netstat -ano | findstr :{port}',
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            # Extract PID from netstat output
            lines = result.stdout.strip().split('\n')
            pids = set()
            for line in lines:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid.isdigit() and pid != '0':
                        pids.add(pid)
            
            for pid in pids:
                try:
                    subprocess.run(f'taskkill /PID {pid} /F', shell=True, capture_output=True)
                    print(f"  ✅ Stopped process {pid}")
                    stopped += 1
                except:
                    print(f"  ⚠️  Could not stop process {pid}")
        else:
            print(f"  ℹ️  No process found on port {port}")
            
    except Exception as e:
        print(f"  ❌ Error: {e}")

print("\n" + "="*60)
if stopped > 0:
    print(f"✅ Stopped {stopped} service(s)")
    print("\nTo restart services:")
    print("  python start_all.py")
else:
    print("ℹ️  No services were running")
print("="*60 + "\n")
