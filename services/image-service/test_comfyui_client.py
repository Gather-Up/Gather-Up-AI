"""
Direct test of ComfyUIClient with fixed node detection
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from services.comfyui_client import ComfyUIClient
from dotenv import load_dotenv
import os

load_dotenv()

async def test():
    client = ComfyUIClient(
        base_url="http://127.0.0.1:8000",
        timeout=120.0
    )
    
    # Load models from environment
    text_encoder = os.getenv("TEXT_ENCODER_MODEL", "qwen_3_4b.safetensors")
    diffusion = os.getenv("DIFFUSION_MODEL", "z_image_turbo_bf16.safetensors")
    vae = os.getenv("VAE_MODEL", "ae.safetensors")
    
    print("Testing ComfyUI image generation...")
    print(f"Text Encoder: {text_encoder}")
    print(f"Diffusion Model: {diffusion}")
    print(f"VAE: {vae}")
    print()
    
    try:
        result = await client.generate_image(
            prompt="birthday party with colorful balloons",
            text_encoder_model=text_encoder,
            diffusion_model=diffusion,
            vae_model=vae,
            width=512,
            height=512
        )
        
        print(f"✅ Success!")
        print(f"   Filename: {result['filename']}")
        print(f"   Prompt ID: {result['prompt_id']}")
        print(f"   Image size: {len(result['image_data'])} bytes")
        
        # Save the image locally to verify
        with open("test_output.png", "wb") as f:
            f.write(result['image_data'])
        print(f"   Saved to: test_output.png")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
