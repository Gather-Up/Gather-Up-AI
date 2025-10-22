from sentence_transformers import SentenceTransformer
import numpy as np
import torch
import os
from dotenv import load_dotenv
load_dotenv()

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME")
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE")
EMBEDDING_REQUIRE_GPU = os.getenv("EMBEDDING_REQUIRE_GPU").lower() == "true"

# Determine device based on GPU availability and configuration
if EMBEDDING_REQUIRE_GPU:
    # Strict GPU-only mode  
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA GPU is not available! This system requires NVIDIA GPU.\n"
            "Please install CUDA and PyTorch with GPU support.\n"
            "Or set EMBEDDING_REQUIRE_GPU=False in .env to allow CPU fallback."
        )
    device = 'cuda'
    print(f"✓ Embedding Model Configuration (from .env):")
    print(f"  - Model: {EMBEDDING_MODEL_NAME}")
    print(f"  - GPU Detected: {torch.cuda.get_device_name(0)}")
    print(f"  - CUDA Version: {torch.version.cuda}")
    print(f"  - Device: {device} (GPU-ONLY mode)")
    print(f"  - Require GPU: {EMBEDDING_REQUIRE_GPU}")
else:

    if torch.cuda.is_available() and EMBEDDING_DEVICE == "cuda":
        device = 'cuda'
        print(f"✓ Embedding Model Configuration (from .env):")
        print(f"  - Model: {EMBEDDING_MODEL_NAME}")
        print(f"  - GPU Detected: {torch.cuda.get_device_name(0)}")
        print(f"  - CUDA Version: {torch.version.cuda}")
        print(f"  - Device: {device} (GPU mode with CPU fallback allowed)")
    else:
        device = 'cpu'
        print(f"  Embedding Model Configuration (from .env):")
        print(f"  - Model: {EMBEDDING_MODEL_NAME}")
        print(f"  - GPU: Not available or disabled")
        print(f"  - Device: {device} (CPU mode)")
        print(f"  - Performance: ~10-20x slower than GPU")
        print(f"  - To use GPU: Install CUDA and set EMBEDDING_DEVICE=cuda in .env")

embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=device)

def generate_embedding(text: str) -> list:
    """
    Generate semantic embedding for text using GPU acceleration if available.
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    
    embedding = embedding_model.encode(text, convert_to_tensor=True, device=device)
    return embedding.cpu().tolist()

def compute_similarity(vec1: list, vec2: list) -> float:
    """
    Compute cosine similarity between two vectors.
    Returns a value between -1 and 1, where 1 means identical.
    """
    a = np.array(vec1)
    b = np.array(vec2)
    
    # Handle edge cases
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(np.dot(a, b) / (norm_a * norm_b))
