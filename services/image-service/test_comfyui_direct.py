"""
Direct test of ComfyUI workflow
"""
import requests
import json
import uuid

# Simple working workflow for testing
workflow = {
    "3": {
        "inputs": {
            "seed": 123456,
            "steps": 4,
            "cfg": 1.0,
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": 1.0,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0]
        },
        "class_type": "KSampler"
    },
    "4": {
        "inputs": {
            "ckpt_name": "z_image_turbo_bf16.safetensors"
        },
        "class_type": "CheckpointLoaderSimple"
    },
    "5": {
        "inputs": {
            "width": 512,
            "height": 512,
            "batch_size": 1
        },
        "class_type": "EmptyLatentImage"
    },
    "6": {
        "inputs": {
            "text": "birthday party with balloons and decorations",
            "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode"
    },
    "7": {
        "inputs": {
            "text": "",
            "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode"
    },
    "8": {
        "inputs": {
            "samples": ["3", 0],
            "vae": ["4", 2]
        },
        "class_type": "VAEDecode"
    },
    "9": {
        "inputs": {
            "filename_prefix": "ComfyUI",
            "images": ["8", 0]
        },
        "class_type": "SaveImage"
    }
}

print("Testing ComfyUI workflow...")
print(json.dumps(workflow, indent=2))

response = requests.post(
    "http://127.0.0.1:8000/prompt",
    json={
        "prompt": workflow,
        "client_id": str(uuid.uuid4())
    }
)

print(f"\nStatus: {response.status_code}")
print(f"Response: {response.text}")
