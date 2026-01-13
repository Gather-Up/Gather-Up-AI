"""
Check what nodes and models are available in your ComfyUI
"""
import requests
import json

print("Checking your ComfyUI setup...")
print()

# Get object info
response = requests.get("http://127.0.0.1:8000/object_info")
nodes = response.json()

# Check for Z-Image Turbo compatible loaders
print("Available loaders:")
print("-" * 70)

relevant_nodes = ['UNETLoader', 'DualCLIPLoader', 'CLIPLoader', 'VAELoader', 
                  'CheckpointLoaderSimple', 'TripleCLIPLoader']

for node_name in relevant_nodes:
    if node_name in nodes:
        node_info = nodes[node_name]
        print(f"\n✅ {node_name}")
        
        if 'input' in node_info and 'required' in node_info['input']:
            print("   Inputs:")
            for input_name, input_info in node_info['input']['required'].items():
                if isinstance(input_info, list) and len(input_info) > 0:
                    if isinstance(input_info[0], list):
                        # It's a list of options
                        options = input_info[0]
                        print(f"     - {input_name}: {options[:3]}{'...' if len(options) > 3 else ''}")
                    else:
                        print(f"     - {input_name}: {input_info[0]}")

print()
print("=" * 70)
print()

# Now check what models are available
print("Checking available models...")
print()

# Check for UNET models
if 'UNETLoader' in nodes:
    unet_info = nodes['UNETLoader']
    if 'input' in unet_info and 'required' in unet_info['input']:
        unet_options = unet_info['input']['required'].get('unet_name', [[]])[0]
        print(f"UNET Models: {unet_options}")

# Check for CLIP models  
if 'DualCLIPLoader' in nodes:
    clip_info = nodes['DualCLIPLoader']
    if 'input' in clip_info and 'required' in clip_info['input']:
        clip1_options = clip_info['input']['required'].get('clip_name1', [[]])[0]
        print(f"CLIP Models: {clip1_options}")
        
        # Check type options
        type_options = clip_info['input']['required'].get('type', [[]])[0]
        print(f"CLIP Types: {type_options}")

# Check for VAE models
if 'VAELoader' in nodes:
    vae_info = nodes['VAELoader']
    if 'input' in vae_info and 'required' in vae_info['input']:
        vae_options = vae_info['input']['required'].get('vae_name', [[]])[0]
        print(f"VAE Models: {vae_options}")

print()
print("=" * 70)
print()

# Create a test workflow
print("Creating test Z-Image Turbo workflow...")
print()

# Determine the correct CLIP type
clip_type = "sd3"  # Default
if 'DualCLIPLoader' in nodes:
    clip_info = nodes['DualCLIPLoader']
    if 'input' in clip_info and 'required' in clip_info['input']:
        type_options = clip_info['input']['required'].get('type', [[]])[0]
        if type_options:
            # Use the first available type, or sd3 if available
            if 'sd3' in type_options:
                clip_type = 'sd3'
            elif 'sdxl' in type_options:
                clip_type = 'sdxl'
            else:
                clip_type = type_options[0]

print(f"Using CLIP type: {clip_type}")
print()

# Save the recommended workflow
workflow = {
    "1": {
        "inputs": {
            "unet_name": "z_image_turbo_bf16.safetensors",
            "weight_dtype": "default"
        },
        "class_type": "UNETLoader"
    },
    "2": {
        "inputs": {
            "clip_name1": "qwen_3_4b.safetensors",
            "clip_name2": "qwen_3_4b.safetensors",
            "type": clip_type
        },
        "class_type": "DualCLIPLoader"
    },
    "3": {
        "inputs": {
            "vae_name": "ae.safetensors"
        },
        "class_type": "VAELoader"
    },
    "4": {
        "inputs": {
            "text": "test prompt",
            "clip": ["2", 0]
        },
        "class_type": "CLIPTextEncode"
    },
    "5": {
        "inputs": {
            "text": "",
            "clip": ["2", 0]
        },
        "class_type": "CLIPTextEncode"
    },
    "6": {
        "inputs": {
            "width": 512,
            "height": 512,
            "batch_size": 1
        },
        "class_type": "EmptyLatentImage"
    },
    "7": {
        "inputs": {
            "seed": 12345,
            "steps": 4,
            "cfg": 1.0,
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": 1.0,
            "model": ["1", 0],
            "positive": ["4", 0],
            "negative": ["5", 0],
            "latent_image": ["6", 0]
        },
        "class_type": "KSampler"
    },
    "8": {
        "inputs": {
            "samples": ["7", 0],
            "vae": ["3", 0]
        },
        "class_type": "VAEDecode"
    },
    "9": {
        "inputs": {
            "filename_prefix": "z_image_test",
            "images": ["8", 0]
        },
        "class_type": "SaveImage"
    }
}

with open("z_image_workflow.json", "w") as f:
    json.dump(workflow, f, indent=2)

print("✅ Saved Z-Image Turbo workflow to: z_image_workflow.json")
print()
print("Testing it now...")

import uuid
test_response = requests.post(
    "http://127.0.0.1:8000/prompt",
    json={
        "prompt": workflow,
        "client_id": str(uuid.uuid4())
    }
)

if test_response.status_code == 200:
    result = test_response.json()
    print(f"✅ SUCCESS! Workflow accepted!")
    print(f"   Prompt ID: {result.get('prompt_id')}")
    print()
    print("This workflow will be used in your service!")
else:
    print(f"❌ Error: {test_response.status_code}")
    print(test_response.text[:500])
