"""
Test that mimics exactly what the service does
"""
import asyncio
import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from services.comfyui_client import ComfyUIClient
from dotenv import load_dotenv
import os

# Set up logging like the service
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

async def test():
    print("="*70)
    print("Testing EXACTLY like the service does")
    print("="*70)
    
    # Initialize client exactly like the service
    client = ComfyUIClient(
        base_url=os.getenv("COMFYUI_URL", "http://127.0.0.1:8000"),
        timeout=int(os.getenv("COMFYUI_TIMEOUT", "300"))
    )
    
    # Check connection
    connected = await client.check_connection()
    print(f"\nConnection status: {connected}")
    
    if not connected:
        print("❌ Cannot connect to ComfyUI!")
        return
    
    # Generate image exactly like the route does
    try:
        print("\nGenerating image...")
        result = await client.generate_image(
            prompt="a beautiful sunset over mountains",
            text_encoder_model=os.getenv("TEXT_ENCODER_MODEL", "qwen_3_4b.safetensors"),
            diffusion_model=os.getenv("DIFFUSION_MODEL", "z_image_turbo_bf16.safetensors"),
            vae_model=os.getenv("VAE_MODEL", "ae.safetensors"),
            width=1024,
            height=1024,
            seed=None
        )
        
        print(f"\n✅ SUCCESS!")
        print(f"Filename: {result['filename']}")
        print(f"Prompt ID: {result['prompt_id']}")
        print(f"Image size: {len(result['image_data'])} bytes")
        
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
