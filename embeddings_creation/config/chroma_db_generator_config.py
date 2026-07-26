CHROMA_DATA_PATH = "chroma_db/"

# for details on the meaning of these 3 metnods, visit:
# https://docs.trychroma.com/usage-guide
vector_similarity = {
    "cosine_similarity": {"hnsw:space": "cosine"},
    "l2_norm": {"hnsw:space": "l2"},
    "inner_product": {"hnsw:space": "ip"},
}