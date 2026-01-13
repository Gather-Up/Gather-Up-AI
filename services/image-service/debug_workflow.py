"""
Debug script to test workflow and see actual ComfyUI response
"""
import asyncio
import httpx
import json
from datetime import datetime

async def test_workflow():
    base_url = "http://127.0.0.1:8000"
    
    # Create the exact workflow your service uses
    seed = int(datetime.now().timestamp() * 1000000) % 2**32
    prompt = "Create a stunning visual for a wedding event in Kandy with elegant decorations"
    
    workflow = {
        "1": {  # Load UNET Model
            "inputs": {
                "unet_name": "z_image_turbo_bf16.safetensors",
                "weight_dtype": "default"
            },
            "class_type": "UNETLoader"
        },
        "2": {  # Load CLIP Model
            "inputs": {
                "clip_name": "qwen_3_4b.safetensors",
                "type": "sd3"
            },
            "class_type": "CLIPLoader"
        },
        "3": {  # Load VAE
            "inputs": {
                "vae_name": "ae.safetensors"
            },
            "class_type": "VAELoader"
        },
        "4": {  # Positive Prompt
            "inputs": {
                "text": prompt,
                "clip": ["2", 0]
            },
            "class_type": "CLIPTextEncode"
        },
        "5": {  # Negative Prompt
            "inputs": {
                "text": "",
                "clip": ["2", 0]
            },
            "class_type": "CLIPTextEncode"
        },
        "6": {  # Empty Latent Image
            "inputs": {
                "width": 1024,
                "height": 1024,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage"
        },
        "7": {  # KSampler
            "inputs": {
                "seed": seed,
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
        "8": {  # VAE Decode
            "inputs": {
                "samples": ["7", 0],
                "vae": ["3", 0]
            },
            "class_type": "VAEDecode"
        },
        "9": {  # Save Image
            "inputs": {
                "filename_prefix": "gatherup_ai",
                "images": ["8", 0]
            },
            "class_type": "SaveImage"
        }
    }
    
    print("=" * 60)
    print("Testing ComfyUI Workflow")
    print("=" * 60)
    
    # 1. Queue the prompt
    print("\n1. Queuing prompt...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{base_url}/prompt",
            json={"prompt": workflow, "client_id": "debug_test"}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"ERROR: {response.text}")
            return
        
        result = response.json()
        prompt_id = result.get("prompt_id")
        print(f"✓ Queued with ID: {prompt_id}")
    
    # 2. Wait for completion
    print("\n2. Waiting for completion...")
    max_wait = 60
    check_interval = 2
    elapsed = 0
    
    while elapsed < max_wait:
        await asyncio.sleep(check_interval)
        elapsed += check_interval
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{base_url}/history/{prompt_id}")
            history = response.json()
            
            if prompt_id in history:
                prompt_history = history[prompt_id]
                status = prompt_history.get("status", {})
                status_str = status.get("status_str", "unknown")
                
                print(f"   Status: {status_str} (waited {elapsed}s)")
                
                if status_str == "success":
                    print("\n3. Workflow completed!")
                    print("\n" + "=" * 60)
                    print("HISTORY STRUCTURE:")
                    print("=" * 60)
                    print(json.dumps(prompt_history, indent=2)[:2000])
                    print("\n" + "=" * 60)
                    
                    # Check outputs structure
                    outputs = prompt_history.get("outputs", {})
                    print(f"\nOutputs keys: {list(outputs.keys())}")
                    
                    for node_id, output in outputs.items():
                        print(f"\nNode {node_id}:")
                        print(f"  Type: {type(output)}")
                        print(f"  Keys: {list(output.keys()) if isinstance(output, dict) else 'N/A'}")
                        
                        if isinstance(output, dict) and "images" in output:
                            images = output["images"]
                            print(f"  Images count: {len(images)}")
                            if images:
                                print(f"  First image info: {images[0]}")
                    
                    return
                
                elif status_str == "error":
                    print(f"\nERROR: Workflow failed")
                    print(json.dumps(status, indent=2))
                    return
    
    print(f"\nTimeout after {max_wait}s")

if __name__ == "__main__":
    asyncio.run(test_workflow())
