"""
Direct test Z-Image Turbo workflow with ComfyUI
"""
import requests
import json
import uuid

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
            "type": "flux"
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
            "text": "birthday party with colorful balloons and decorations",
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
            "seed": 123456,
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
            "filename_prefix": "z_image_turbo_test",
            "images": ["8", 0]
        },
        "class_type": "SaveImage"
    }
}

print("Testing Z-Image Turbo workflow directly...")
print(json.dumps(workflow, indent=2)[:1000])
print()

response = requests.post(
    "http://127.0.0.1:8000/prompt",
    json={
        "prompt": workflow,
        "client_id": str(uuid.uuid4())
    }
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"✅ SUCCESS! Prompt ID: {result.get('prompt_id')}")
    print("Image should be generating...")
else:
    print(f"❌ FAILED")
    print(response.text[:2000])
