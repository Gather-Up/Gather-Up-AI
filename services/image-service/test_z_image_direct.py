"""
Direct test of Z-Image Turbo workflow
"""
import asyncio
import httpx
import json
import time

async def test_z_image():
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
                "type": "sd3"
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
                "text": "a beautiful sunset over mountains",
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
    
    print("Queuing Z-Image Turbo workflow...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://127.0.0.1:8000/prompt",
            json={
                "prompt": workflow,
                "client_id": "test_client"
            }
        )
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return
        
        result = response.json()
        prompt_id = result["prompt_id"]
        print(f"✅ Queued with ID: {prompt_id}")
        print()
        
        # Wait for completion
        print("Waiting for generation...")
        for i in range(30):
            await asyncio.sleep(2)
            
            history_response = await client.get(
                f"http://127.0.0.1:8000/history/{prompt_id}"
            )
            
            if history_response.status_code == 200:
                history = history_response.json()
                
                if prompt_id in history:
                    prompt_history = history[prompt_id]
                    
                    if "outputs" in prompt_history:
                        print("✅ Generation complete!")
                        print()
                        print("Outputs:", json.dumps(prompt_history["outputs"], indent=2))
                        
                        # Get the image
                        outputs = prompt_history["outputs"]
                        if "9" in outputs:
                            images = outputs["9"]["images"]
                            if images:
                                filename = images[0]["filename"]
                                print(f"\n✅ Image saved: {filename}")
                                
                                # Download it
                                img_response = await client.get(
                                    "http://127.0.0.1:8000/view",
                                    params={"filename": filename, "type": "output"}
                                )
                                
                                if img_response.status_code == 200:
                                    with open(f"test_output_{filename}", "wb") as f:
                                        f.write(img_response.content)
                                    print(f"✅ Downloaded: test_output_{filename}")
                                    print(f"   Size: {len(img_response.content)} bytes")
                        return
                    
                    if "status" in prompt_history:
                        status = prompt_history["status"]
                        if status.get("status_str") == "error":
                            print(f"❌ Error: {status.get('messages')}")
                            return
            
            print(f"   Waiting... ({i*2}s)")
        
        print("❌ Timeout waiting for completion")

if __name__ == "__main__":
    asyncio.run(test_z_image())
