"""
Check ComfyUI history response structure
"""
import requests
import json
import time

# Get recent prompts from queue history
response = requests.get("http://127.0.0.1:8000/queue")
print("Queue response:")
print(json.dumps(response.json(), indent=2)[:500])

# Check history endpoint
history_response = requests.get("http://127.0.0.1:8000/history")
history_data = history_response.json()

print("\n" + "="*60)
print("Recent Workflow History:")
print("="*60)

# Get the most recent prompt
if history_data:
    recent_key = list(history_data.keys())[0]
    recent = history_data[recent_key]
    
    print(f"\nPrompt ID: {recent_key}")
    print(f"\nOutputs keys: {list(recent.get('outputs', {}).keys())}")
    
    print(f"\nFull history structure:")
    print(json.dumps(recent, indent=2)[:2000])
else:
    print("No history found")
