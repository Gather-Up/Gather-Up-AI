"""
Check specific workflow history
"""
import requests
import json

prompt_ids = [
    "94fed332-998e-4523-b7b1-93ce3957f899",  # Latest with CLIPLoader (SUCCESS!)
]

for prompt_id in prompt_ids:
    print(f"\nWorkflow: {prompt_id}")
    print("=" * 70)
    
    response = requests.get(f"http://127.0.0.1:8000/history/{prompt_id}")
    
    if response.status_code == 200:
        history = response.json()
        
        if prompt_id in history:
            data = history[prompt_id]
            
            print("\nStatus:", data.get("status"))
            print("\nOutputs:", json.dumps(data.get("outputs", {}), indent=2))
            
            if "prompt" in data and isinstance(data["prompt"], dict):
                print("\nWorkflow nodes:")
                for node_id in sorted(data["prompt"].keys(), key=lambda x: int(x)):
                    node = data["prompt"][node_id]
                    print(f"  Node {node_id}: {node['class_type']}")
        else:
            print("  Not found in history")
    else:
        print(f"  Error: {response.status_code}")
