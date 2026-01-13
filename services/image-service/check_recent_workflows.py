import requests
import json

r = requests.get('http://127.0.0.1:8000/history')
h = r.json()
keys = list(h.keys())

print(f"Total prompts in history: {len(keys)}")
print()

# Check recent prompts
for i, key in enumerate(keys[:3]):
    entry = h[key]
    prompt = entry.get('prompt', [])
    workflow = prompt[2] if len(prompt) > 2 else {}
    outputs = entry.get('outputs', {})
    status = entry.get('status', {})
    
    print(f"{i+1}. Prompt ID: {key}")
    print(f"   Workflow nodes: {list(workflow.keys())}")
    print(f"   Output nodes: {list(outputs.keys())}")
    print(f"   Status: {status.get('status_str')}")
    
    # Check if it has UNETLoader (Z-Image Turbo)
    has_unet = any('UNETLoader' == workflow.get(node_id, {}).get('class_type') for node_id in workflow.keys())
    print(f"   Uses Z-Image Turbo: {has_unet}")
    print()
