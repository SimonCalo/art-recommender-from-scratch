import numpy as np


def normalize_vector(v: np.ndarray) -> np.ndarray:
    """
    Normalize a vector.

    Args:
        v (np.ndarray): Input vector.

    Returns:
        np.ndarray: Normalized vector.
    """
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm


def create_normalized_vector(vectors: list[np.ndarray]) -> np.ndarray:
    """
    Create a normalized vector by adding together a list of vectors.

    Args:
        vectors (list[np.ndarray]): List of input vectors.

    Returns:
        np.ndarray: Normalized vector.
    """
    # Convert the list of vectors to a NumPy array
    vectors_array = np.array(vectors)
    
    # Sum the vectors along the first axis (axis=0)
    summed_vector = np.sum(vectors_array, axis=0)
    
    # Normalize the summed vector
    normalized_vector = normalize_vector(summed_vector)
    
    return normalized_vector


def compute_cosine_similarities(vectors1: np.ndarray, vectors2: np.ndarray) -> np.ndarray:
    """Compute cosine similarities between two sets of vectors using vectorized operations.

    The computation follows these steps:
    1. Normalize each vector by dividing by its length.
    2. Compute dot products between all pairs using matrix multiplication.
       - Result[i,j] = dot(vectors1[i], vectors2[j]).
    
    Since vectors are normalized, this directly gives cosine similarity.
    
    Args:
        vectors1 (np.ndarray): First set of vectors.
        vectors2 (np.ndarray): Second set of vectors to compare against.
        
    Returns:
        np.ndarray: Matrix of cosine similarities between the two sets of vectors.
    """
    norm_vectors1 = (vectors1 / np.linalg.norm(vectors1, axis=1)[:, np.newaxis])
    norm_vectors2 = (vectors2 / np.linalg.norm(vectors2, axis=1)[:, np.newaxis])
    
    return np.dot(norm_vectors1, norm_vectors2.T)
