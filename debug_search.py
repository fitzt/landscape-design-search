
import sys
import os
import requests
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Setup paths
sys.path.append(os.getcwd())
from backend.config import INDEX_PATH, CLIP_MODEL_NAME

def test_direct_logic():
    print("Testing Direct Logic...")
    if not os.path.exists(INDEX_PATH):
        print(f"ERROR: Index file not found at {INDEX_PATH}")
        return

    try:
        index = faiss.read_index(str(INDEX_PATH))
        print(f"Index loaded. ntotal: {index.ntotal}")
    except Exception as e:
        print(f"ERROR loading index: {e}")
        return

    try:
        model = SentenceTransformer(CLIP_MODEL_NAME)
        print("Model loaded.")
    except Exception as e:
        print(f"ERROR loading model: {e}")
        return

    query = "pool"
    query_emb = model.encode([query]).astype('float32')
    faiss.normalize_L2(query_emb)
    
    D, I = index.search(query_emb, 5)
    print(f"Raw Search Results (Distances, IDs):")
    print(D)
    print(I)

def test_api():
    print("\nTesting API...")
    url = "http://localhost:8000/api/search"
    payload = {"query": "pool", "top_k": 5}
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            data = res.json()
            print(f"API Success. Results found: {len(data['results'])}")
            print(data)
        else:
            print(f"API Error {res.status_code}: {res.text}")
    except Exception as e:
        print(f"API Call Failed: {e}")

if __name__ == "__main__":
    test_direct_logic()
    test_api()
