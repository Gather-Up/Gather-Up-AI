from sentence_transformers import SentenceTransformer
import numpy as np

# Load embedding model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def generate_embedding(text: str) -> list:
    embedding = embedding_model.encode(text)
    return embedding.tolist()

def compute_similarity(vec1: list, vec2: list) -> float:
    # Cosine similarity
    a = np.array(vec1)
    b = np.array(vec2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
