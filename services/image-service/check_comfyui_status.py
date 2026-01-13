"""
Check ComfyUI queue and system status
"""
import requests
import json

print("Checking ComfyUI status...")
print("=" * 70)

# Check queue
response = requests.get("http://127.0.0.1:8000/queue")
queue = response.json()

print("\nQueue:")
print(f"  Running: {len(queue.get('queue_running', []))}")
print(f"  Pending: {len(queue.get('queue_pending', []))}")

if queue.get('queue_running'):
    print("\n  Currently running:")
    for item in queue['queue_running']:
        print(f"    - {item}")

# Check system stats
response = requests.get("http://127.0.0.1:8000/system_stats")
stats = response.json()

print("\nSystem Stats:")
print(f"  {json.dumps(stats, indent=2)}")

# Get recent history
response = requests.get("http://127.0.0.1:8000/history")
history = response.json()

print(f"\nRecent workflows: {len(history)}")
for prompt_id, data in list(history.items())[:3]:
    print(f"\n  Workflow: {prompt_id}")
    if "outputs" in data:
        print(f"    Outputs: {list(data['outputs'].keys())}")
        for node_id, output in data['outputs'].items():
            if 'images' in output:
                print(f"      Node {node_id}: {len(output['images'])} images")
    if "status" in data:
        print(f"    Status: {data['status']}")
