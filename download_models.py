from sentence_transformers import SentenceTransformer
import os

def download():
    model_name = "clip-ViT-B-32"
    print(f"Pre-downloading {model_name}...")
    SentenceTransformer(model_name)
    print("Download complete.")

if __name__ == "__main__":
    download()
