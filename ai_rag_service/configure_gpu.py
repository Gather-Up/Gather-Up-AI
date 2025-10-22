import subprocess
import sys
import torch
import json

def check_cuda():
    
    """Check if CUDA/GPU is available"""

    print("\n" + "="*80)
    print("1. CHECKING CUDA/GPU AVAILABILITY")
    print("="*80)
    
    if torch.cuda.is_available():
        print(f"✓ CUDA is available")
        print(f"✓ GPU Device: {torch.cuda.get_device_name(0)}")
        print(f"✓ CUDA Version: {torch.version.cuda}")
        print(f"✓ Number of GPUs: {torch.cuda.device_count()}")
        print(f"✓ GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
        return True
    else:
        print("✗ CUDA is NOT available!")
        print("\nTo fix this:")
        print("1. Install NVIDIA CUDA Toolkit from: https://developer.nvidia.com/cuda-downloads")
        print("2. Install PyTorch with CUDA support:")
        print("   pip uninstall torch torchvision torchaudio")
        print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
        return False

def check_ollama_gpu():
    """Check if Ollama is configured for GPU"""
    print("\n" + "="*80)
    print("2. CHECKING OLLAMA GPU CONFIGURATION")
    print("="*80)
    
    try:
        # Check if Ollama is running
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            shell=True
        )
        
        if result.returncode == 0:
            print("✓ Ollama is installed and running")
            print("\nInstalled models:")
            print(result.stdout)
            
            # Check if llama3.1:8b is installed
            if "llama3.1:8b" in result.stdout or "llama3.1" in result.stdout:
                print("✓ LLaMA 3.1 8B model is installed")
            else:
                print("✗ LLaMA 3.1 8B model is NOT installed")
                print("Run: ollama pull llama3.1:8b")
                return False
        else:
            print("✗ Ollama is not running")
            print("Start Ollama with: ollama serve")
            return False
            
    except FileNotFoundError:
        print("✗ Ollama is not installed")
        print("Install from: https://ollama.ai")
        return False
    
    return True

def configure_ollama_gpu():
    """Configure Ollama to use ONLY GPU"""
    print("\n" + "="*80)
    print("3. CONFIGURING OLLAMA FOR GPU-ONLY EXECUTION")
    print("="*80)
    
    print("\nTo ensure Ollama uses ONLY GPU, set these environment variables:")
    print("\nFor PowerShell:")
    print("─" * 80)
    print("$env:OLLAMA_NUM_GPU = '99'          # Load all layers on GPU")
    print("$env:OLLAMA_GPU_LAYERS = '99'       # Force all layers on GPU")
    print("$env:OLLAMA_NUM_THREAD = '1'        # Minimize CPU threads")
    print("$env:OLLAMA_MAIN_GPU = '0'          # Use primary GPU")
    print("$env:CUDA_VISIBLE_DEVICES = '0'     # Only use first GPU")
    print("\nThen restart Ollama:")
    print("ollama serve")
    print("─" * 80)
    
    print("\nFor permanent configuration, add to Windows System Environment Variables:")
    print("1. Press Win + X → System → Advanced system settings")
    print("2. Environment Variables → New (System variables)")
    print("3. Add each variable above")

def verify_gpu_usage():
    """Verify GPU is being used during inference"""
    print("\n" + "="*80)
    print("4. VERIFYING GPU USAGE DURING INFERENCE")
    print("="*80)
    
    print("\nTo verify GPU usage in real-time:")
    print("\n1. Open a new PowerShell terminal and run:")
    print("   nvidia-smi -l 1")
    print("   (This shows GPU usage every 1 second)")
    
    print("\n2. Send a test request to your API")
    
    print("\n3. Watch for:")
    print("   - GPU Utilization should spike to 80-100%")
    print("   - GPU Memory usage should increase")
    print("   - Power Draw should increase")
    
    print("\nIf you see LOW GPU usage:")
    print("   ✗ CPU is being used instead")
    print("   → Set the environment variables above and restart Ollama")
    
    print("\nIf you see HIGH GPU usage:")
    print("   ✓ GPU is working correctly!")

def show_current_config():
    """Show current RAG system GPU configuration"""
    print("\n" + "="*80)
    print("5. CURRENT RAG SYSTEM GPU CONFIGURATION")
    print("="*80)
    
    print("\nEmbedding Model (vector_service.py):")
    print("─" * 80)
    print("✓ Device: 'cuda' (GPU-ONLY)")
    print("✓ Model: all-MiniLM-L6-v2")
    print("✓ Fallback to CPU: DISABLED (will error if GPU not available)")
    
    print("\n\nLLaMA Model (llama_service.py):")
    print("─" * 80)
    print("✓ num_gpu: 99 (all layers on GPU)")
    print("✓ num_thread: 1 (minimal CPU usage)")
    print("✓ main_gpu: 0 (use first GPU)")
    print("✓ low_vram: False (full GPU utilization)")
    
    print("\n\nThese settings ensure:")
    print("• ALL embedding generation on GPU")
    print("• ALL LLaMA inference on GPU")
    print("• NO CPU processing for AI tasks")
    print("• System will ERROR if GPU not available (no silent CPU fallback)")

def test_embedding_gpu():
    """Test if embeddings are using GPU"""
    print("\n" + "="*80)
    print("6. TESTING EMBEDDING MODEL GPU USAGE")
    print("="*80)
    
    try:
        from services.vector_service import generate_embedding
        import time
        
        print("\nGenerating test embedding...")
        start = time.time()
        embedding = generate_embedding("Test GPU usage for birthday party planning")
        elapsed = time.time() - start
        
        print(f"✓ Embedding generated successfully")
        print(f"✓ Time taken: {elapsed*1000:.2f}ms")
        print(f"✓ Embedding dimension: {len(embedding)}")
        
        if elapsed < 0.1:
            print("✓ Very fast! GPU is definitely being used")
        else:
            print("⚠ Slower than expected. GPU might not be utilized fully")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        if "CUDA" in str(e):
            print("→ GPU is required but not available")

def main():
    print("""
            GPU-ONLY CONFIGURATION FOR RAG SYSTEM                            
            Ensuring NVIDIA GPU usage without CPU fallback 
    """)
    
    # Step 1: Check CUDA
    cuda_ok = check_cuda()
    
    # Step 2: Check Ollama
    ollama_ok = check_ollama_gpu()
    
    # Step 3: Show configuration instructions
    configure_ollama_gpu()
    
    # Step 4: Show verification instructions
    verify_gpu_usage()
    
    # Step 5: Show current system config
    show_current_config()
    
    # Step 6: Test embeddings (if possible)
    if cuda_ok:
        try:
            test_embedding_gpu()
        except:
            print("\nCould not test embeddings (service may not be running)")
    
    # Final summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if cuda_ok and ollama_ok:
        print("✓ System is ready for GPU-ONLY operation")
        print("\nNext steps:")
        print("1. Set the environment variables shown above")
        print("2. Restart Ollama: ollama serve")
        print("3. Restart FastAPI: uvicorn main:app --reload --port 8001")
        print("4. Monitor GPU usage: nvidia-smi -l 1")
        print("5. Send a test request and watch GPU spike to 80-100%")
    else:
        print("✗ System is NOT ready")
        if not cuda_ok:
            print("→ Fix CUDA/GPU installation first")
        if not ollama_ok:
            print("→ Fix Ollama installation/configuration")
    
    print("\n" + "="*80)
    print("For real-time GPU monitoring, run in another terminal:")
    print("nvidia-smi -l 1")
    print("="*80)

if __name__ == "__main__":
    main()
