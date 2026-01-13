"""
Direct test of ComfyUIClient to debug the issue
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from services.comfyui_client import ComfyUIClient

async def test_client():
    print("=" * 70)
    print("Testing ComfyUIClient directly")
    print("=" * 70)
    
    client = ComfyUIClient("http://127.0.0.1:8000", timeout=300)
    
    # Check connection
    print("\n1. Checking connection...")
    connected = await client.check_connection()
    print(f"   Connected: {connected}")
    
    if not connected:
        print("   ERROR: Cannot connect to ComfyUI")
        return
    
    # Test image generation
    print("\n2. Generating image...")
    prompt = "A beautiful wedding venue in Kandy, Sri Lanka, with elegant decorations"
    
    try:
        result = await client.generate_image(
            prompt=prompt,
            text_encoder_model="qwen_3_4b.safetensors",
            diffusion_model="z_image_turbo_bf16.safetensors",
            vae_model="ae.safetensors",
            width=1024,
            height=1024
        )
        
        print("\n✅ SUCCESS!")
        print(f"   Prompt ID: {result['prompt_id']}")
        print(f"   Filename: {result['filename']}")
        print(f"   Image size: {len(result['image_data'])} bytes")
        print(f"   Seed: {result['seed']}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_client())
