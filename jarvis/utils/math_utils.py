import numpy as np

def cosine_similarity(v1, v2):
    """Compute cosine similarity between two vectors."""
    if v1 is None or v2 is None:
        return 0.0
    a = np.array(v1)
    b = np.array(v2)
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))
