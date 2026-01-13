"""
Extract working Z-Image Turbo workflow from ComfyUI
This will get the exact workflow structure that works in your ComfyUI
"""
import requests
import json

print("=" * 70)
print("Getting your working ComfyUI workflow structure")
print("=" * 70)
print()

# Get the most recent successful workflow from ComfyUI history
response = requests.get("http://127.0.0.1:8000/history")
history = response.json()

if not history:
    print("❌ No workflow history found")
    print()
    print("Please:")
    print("1. Open ComfyUI in your browser (http://127.0.0.1:8000)")
    print("2. Generate an image with your Z-Image Turbo workflow")
    print("3. Run this script again")
    exit(1)

# Find the most recent successful workflow
print("Looking for successful Z-Image Turbo workflows...")
print()

for prompt_id, entry in list(history.items())[:10]:
    status = entry.get('status', {})
    if status.get('status_str') == 'success':
        prompt_data = entry.get('prompt', [])
        if len(prompt_data) > 2:
            workflow = prompt_data[2]
            
            # Check if it uses Z-Image Turbo models
            has_z_image = False
            for node_id, node in workflow.items():
                node_inputs = node.get('inputs', {})
                for key, value in node_inputs.items():
                    if isinstance(value, str) and 'z_image_turbo' in value.lower():
                        has_z_image = True
                        break
            
            if has_z_image or True:  # Take the first successful one
                print(f"✅ Found working workflow: {prompt_id}")
                print()
                print("Workflow structure:")
                print("-" * 70)
                
                # Analyze the workflow
                for node_id in sorted(workflow.keys(), key=lambda x: int(x) if x.isdigit() else 999):
                    node = workflow[node_id]
                    class_type = node.get('class_type', 'Unknown')
                    inputs = node.get('inputs', {})
                    
                    print(f"Node {node_id}: {class_type}")
                    for key, value in inputs.items():
                        if isinstance(value, str) and len(value) < 100:
                            print(f"  - {key}: {value}")
                        elif isinstance(value, (int, float, bool)):
                            print(f"  - {key}: {value}")
                        elif isinstance(value, list) and len(value) == 2:
                            print(f"  - {key}: [Node {value[0]}, output {value[1]}]")
                
                print()
                print("-" * 70)
                print()
                
                # Save the workflow
                with open("working_workflow.json", "w") as f:
                    json.dump(workflow, f, indent=2)
                
                print("✅ Saved to: working_workflow.json")
                print()
                print("Next steps:")
                print("1. Check working_workflow.json")
                print("2. I'll update the service to use this exact structure")
                
                # Show the workflow
                print()
                print("Full workflow JSON:")
                print(json.dumps(workflow, indent=2))
                
                exit(0)

print("❌ No successful Z-Image Turbo workflows found")
print()
print("Please generate an image in ComfyUI first with your Z-Image Turbo models")
