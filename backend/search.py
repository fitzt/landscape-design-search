import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from .config import INDEX_PATH, CLIP_MODEL_NAME, DEFAULT_TOP_K
from .db import get_db_connection
import psycopg2.extras
from PIL import Image
import os

class SearchEngine:
    def __init__(self):
        self.model = None
        self.index = None
        self.load_resources()

    def load_resources(self):
        if INDEX_PATH.exists():
            print(f"Loading index from {INDEX_PATH}")
            self.index = faiss.read_index(str(INDEX_PATH))
        else:
            print("WARNING: No index found. Search will return empty.")
        
        print(f"Loading CLIP model: {CLIP_MODEL_NAME}...")
        self.model = SentenceTransformer(CLIP_MODEL_NAME)
        print("Model loaded.")

    def search(self, query: str, top_k: int = DEFAULT_TOP_K, favorites_only: bool = False, folder: str = None, project_slug: str = None):
        if not self.index or not self.model:
            print("Search Error: Index or Model missing")
            return []

        # CASE 1: No Query (Browse Mode or Project Mode base view)
        if not query:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if project_slug:
                    # STRICT: Exact match on project_slug column
                    cur.execute("SELECT * FROM images WHERE project_slug = %s ORDER BY file_path ASC", (project_slug,))
                elif folder:
                    cur.execute("SELECT * FROM images WHERE folder = %s ORDER BY id", (folder,))
                else:
                    cur.execute("SELECT * FROM images ORDER BY id LIMIT %s", (top_k,))
                rows = cur.fetchall()
            conn.close()
            return [dict(r) for r in rows]

        # CASE 2: Semantic Search
        # Encode Query
        query_emb = self.model.encode([query])
        query_emb = query_emb.astype('float32')
        faiss.normalize_L2(query_emb)

        # Search in FAISS
        search_k = top_k * 4
        distances, ids = self.index.search(query_emb, search_k)
        
        ids = ids[0]
        distances = distances[0]
        
        # Fetch Metadata
        valid_ids = [int(i) for i in ids if i >= 0]
        if not valid_ids:
            return []

        # Get all candidates
        conn = get_db_connection()
        placeholders = ','.join(['%s'] * len(valid_ids))
        query_sql = f"SELECT * FROM images WHERE id IN ({placeholders})"
        
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(query_sql, tuple(valid_ids))
            rows = cur.fetchall()
        conn.close()

        row_map = {r['id']: dict(r) for r in rows}
        
        results = []
        for score, img_id in zip(distances, ids):
            if img_id < 0: continue
            if img_id not in row_map: continue
            
            img = row_map[img_id]
            if favorites_only and not img['favorite']: continue
            if folder and not img['file_path'].startswith(folder): continue
            
            # Project Slug Filtering (Strict Exact Match)
            if project_slug:
                if img.get('project_slug') != project_slug:
                    continue

            # Tighten Vector Search: Zero-Leak Threshold
            # For normalized vectors, squared L2 distance d^2 = 2(1 - cos_sim)
            # If we want cos_sim >= 0.8, then d^2 <= 0.4
            SIMILARITY_THRESHOLD = 0.4
            if float(score) > SIMILARITY_THRESHOLD:
                continue
                
            img['score'] = float(score)
            results.append(img)
            
            if len(results) >= top_k:
                break
                
        return results


    def search_by_image(self, image_id: int, top_k: int = DEFAULT_TOP_K):
        """
        Finds similar images using an existing image ID as the anchor.
        Applies "Soft Weights" to boost images from the same folder logic.
        """
        if not self.index or not self.model:
            print("Search Error: Index or Model missing")
            return []

        # 1. Get File Path from DB
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT file_path, folder FROM images WHERE id = %s", (image_id,))
            row = cur.fetchone()
        conn.close()

        if not row:
            print(f"Error: Image ID {image_id} not found.")
            return []
        
        file_path = row[0]
        anchor_folder = row[1]
        
        if file_path.startswith("http"):
            import requests
            from io import BytesIO
            try:
                response = requests.get(file_path)
                response.raise_for_status()
                image = Image.open(BytesIO(response.content))
            except Exception as e:
                print(f"Error fetching image from URL: {e}")
                return []
        else:
            if not os.path.exists(file_path):
                 print(f"Error: File not found at {file_path}")
                 return []
            try:
                image = Image.open(file_path)
            except Exception as e:
                print(f"Error opening local image: {e}")
                return []

        # 2. Encode Image
        try:
            # encoding
            img_emb = self.model.encode([image])
            img_emb = img_emb.astype('float32')
            faiss.normalize_L2(img_emb)
        except Exception as e:
            print(f"Error encoding image: {e}")
            return []

        # 3. Search in FAISS (Fetch more candidates since we re-rank)
        search_k = top_k * 4
        distances, ids = self.index.search(img_emb, search_k)
        
        ids = ids[0]
        distances = distances[0]
        
        # 4. Filter & Fetch Metadata
        valid_ids = [int(i) for i in ids if i >= 0]
        if not valid_ids:
            return []

        conn = get_db_connection()
        placeholders = ','.join(['%s'] * len(valid_ids))
        query_sql = f"SELECT * FROM images WHERE id IN ({placeholders})"
        
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(query_sql, tuple(valid_ids))
            rows = cur.fetchall()
        conn.close()

        row_map = {r['id']: dict(r) for r in rows}
        
        candidates = []
        for score, img_id in zip(distances, ids):
            if img_id < 0: continue
            if img_id == image_id: continue 
            if img_id not in row_map: continue
            
            img = row_map[img_id]
            base_score = float(score)
            
            # --- SOFT WEIGHTS LOGIC ---
            # Boost if same folder (Proxy for same project/type)
            if anchor_folder and img['folder'] == anchor_folder:
                 base_score += 0.08 # +8% Boost (Significant but not overwhelming)

            img['score'] = base_score
            candidates.append(img)
            
        # Re-sort by boosted score (Desc)
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        return candidates[:top_k]

    def analyze_board(self, image_ids: list[int]):
        """
        Zero-shot analysis of a list of images to determine Vibe, Material, and Style.
        Returns a JSON descriptor.
        """
        if not self.model or not image_ids:
            return {}

        try:
            from sentence_transformers import util
            import torch
            
            # define categories
            categories = {
                "Style": ["Modern Minimalist", "Rustic Organic", "Traditional Formal", "Cottage Garden", "Luxury Resort"],
                "Material": ["Natural Stone", "Concrete Pavers", "Wood Decking", "Brick", "Gravel"],
                "Atmosphere": ["Warm & Cozy", "Cool & Sleek", "Bright & Airy", "Moody & Dramatic"]
            }
            
            # Fetch vectors? No, we need to re-encode them or fetch from FAISS?
            # FAISS index stores vectors but random access is tricky without keeping raw vectors in memory.
            # Efficient Hack: Use the file paths again as proxy? No, we want visual analysis.
            # Better Hack: We have to load the images. It's slow but accurate.
            # Optimization: Limit to top 5 images to save time.
            
            limit_ids = image_ids[:5] 
            
            conn = get_db_connection()
            placeholders = ','.join(['%s'] * len(limit_ids))
            with conn.cursor() as cur:
                cur.execute(f"SELECT file_path FROM images WHERE id IN ({placeholders})", tuple(limit_ids))
                rows = cur.fetchall()
            conn.close()
            
            images = []
            for r in rows:
                if os.path.exists(r[0]):
                    try:
                        images.append(Image.open(r[0]))
                    except: pass
            
            if not images:
                return {"error": "No valid images"}
            
            # Encode Images
            img_embs = self.model.encode(images)
            mean_emb = np.mean(img_embs, axis=0) # Centroid of the board
            
            report = {}
            
            for cat, options in categories.items():
                opt_embs = self.model.encode(options)
                sims = util.cos_sim(mean_emb, opt_embs)[0]
                best_idx = int(np.argmax(sims))
                report[cat] = options[best_idx]
                
            return report

        except Exception as e:
            print(f"Analysis Error: {e}")
            return {"error": str(e)}

