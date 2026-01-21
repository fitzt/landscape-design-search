import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from .config import INDEX_PATH, CLIP_MODEL_NAME, DEFAULT_TOP_K, PROJECT_SLUG
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
        # Override project_slug with global config if defined
        if PROJECT_SLUG:
            project_slug = PROJECT_SLUG
            
        if not self.index or not self.model:
            print("Search Error: Index or Model missing")
            return []
            
        # CASE 1: No Query (Browse Mode or Project Mode base view)
        if not query:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                sql = "SELECT * FROM images"
                params = []
                where_clauses = []
                
                if project_slug:
                    where_clauses.append("project_slug = %s")
                    params.append(project_slug)
                
                if folder:
                    where_clauses.append("folder = %s")
                    params.append(folder)
                
                if where_clauses:
                    sql += " WHERE " + " AND ".join(where_clauses)
                
                if project_slug:
                    sql += " ORDER BY file_path ASC"
                else:
                    sql += " ORDER BY id"
                
                if not project_slug and not folder:
                    sql += " LIMIT %s"
                    params.append(top_k)
                    
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
            conn.close()
            return [dict(r) for r in rows]

     # If query is present, use semantic search
        # If query is present, use semantic search
        if query:
            print(f"Executing semantic search for: '{query}'")
            # Encode query
            text_emb = self.model.encode([query]).astype('float32')
            faiss.normalize_L2(text_emb)
            
            # Search index - fetch broadly to allow for post-filtering
            # Since we filter by project_slug AFTER retrieval, we need a large candidate pool.
            # Index size is small (~2k), so fetching 2000 is cheap and safe.
            search_k = max(top_k * 20, 2000)
            D, I = self.index.search(text_emb, search_k)
            
            # Map back to DB images (Semantic Results)
            found_ids = [int(id) for id in I[0] if id != -1]
            scores = {int(id): float(score) for id, score in zip(I[0], D[0]) if id != -1}
            
            # Semantic Fetch
            semantic_results = []
            if found_ids:
                placeholders = ','.join(['%s'] * len(found_ids))
                sql = f"SELECT * FROM images WHERE id IN ({placeholders})"
                params = list(found_ids)
                
                with get_db_connection() as conn:
                    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                        cur.execute(sql, params)
                        semantic_results = [dict(r) for r in cur.fetchall()]

            # Keyword Fetch (Fallback/Boost)
            keyword_results = []
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    # Search filename and rich_tags
                    # Note: We need to handle the array_to_string carefully or just check if it allows text cast
                    # Simplest is ILIKE on filename. For tags, we use array query if possible or cast.
                    kw_sql = """
                        SELECT * FROM images 
                        WHERE (filename ILIKE %s OR array_to_string(rich_tags, ' ') ILIKE %s)
                    """
                    kw_params = [f"%{query}%", f"%{query}%"]
                    
                    if project_slug:
                        kw_sql += " AND project_slug = %s"
                        kw_params.append(project_slug)
                        
                    kw_sql += " LIMIT 20"
                    cur.execute(kw_sql, tuple(kw_params))
                    keyword_results = [dict(r) for r in cur.fetchall()]

            # Merge Results
            final_map = {}
            
            # 1. Add Semantic
            for img in semantic_results:
                # Filter (redundant if sql filtered, but harmless)
                if project_slug and img.get('project_slug') != project_slug: continue
                
                img['similarity'] = scores.get(img['id'], 0)
                # Apply HIGHER threshold to avoid "patios" showing up for "fire pits"
                # 0.15 was too loose. 0.26 was catching pools. 0.25 seems safe and inclusive for Leahy pools.
                if img['similarity'] < 0.25: continue
                
                final_map[img['id']] = img

            # 2. Add/Boost Keyword
            for img in keyword_results:
                if img['id'] in final_map:
                    # Boost existing - heavily favor explicit text matches if we have semantic signal
                    final_map[img['id']]['similarity'] += 0.5 
                else:
                    # Add new - IF it matched a keyword, it's likely relevant even if semantic embedding missed it (rare for CLIP but possible)
                    # But be careful of partial matches. "fire hydrant"?
                    # We'll trust the 20 limit of keyword sql for now.
                    img['similarity'] = 0.45 # Make sure it beats the semantic cutoff
                    final_map[img['id']] = img
            
            # Convert to list and sort
            results = list(final_map.values())
            # Sort descending
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            return results[:top_k]


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
            sql = "SELECT file_path, folder FROM images WHERE id = %s"
            params = [image_id]
            if PROJECT_SLUG:
                sql += " AND project_slug = %s"
                params.append(PROJECT_SLUG)
            cur.execute(sql, tuple(params))
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

            # ALWAYS enforce global PROJECT_SLUG if defined
            if PROJECT_SLUG and img.get('project_slug') != PROJECT_SLUG:
                continue

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
            sql = f"SELECT file_path FROM images WHERE id IN ({placeholders})"
            params = list(limit_ids)
            if PROJECT_SLUG:
                sql += " AND project_slug = %s"
                params.append(PROJECT_SLUG)
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
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


    def search_by_object(self, object_id: str, top_k: int = DEFAULT_TOP_K):
        """
        Finds similar images using a specific object ID as the anchor.
        Queries the image_objects table using pgvector cosine similarity.
        """
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # 1. Get the anchor embedding
                sql = """
                    SELECT io.object_embedding 
                    FROM image_objects io
                    JOIN images i ON io.image_id = i.id
                    WHERE io.id = %s
                """
                params = [object_id]
                if PROJECT_SLUG:
                    sql += " AND i.project_slug = %s"
                    params.append(PROJECT_SLUG)
                
                cur.execute(sql, tuple(params))
                row = cur.fetchone()
                if not row:
                    print(f"Object ID {object_id} not found or access denied.")
                    return []
                anchor_emb = row['object_embedding']

                # 2. Vector search for similar objects
                sql = """
                    SELECT io.image_id, io.label, io.confidence, (io.object_embedding <=> %s) as distance
                    FROM image_objects io
                    JOIN images i ON io.image_id = i.id
                    WHERE io.id != %s
                """
                params = [anchor_emb, object_id]
                if PROJECT_SLUG:
                    sql += " AND i.project_slug = %s"
                    params.append(PROJECT_SLUG)
                
                sql += """
                    ORDER BY io.object_embedding <=> %s
                    LIMIT %s
                """
                params.extend([anchor_emb, top_k * 2])
                
                cur.execute(sql, tuple(params))
                object_results = cur.fetchall()
                
                if not object_results:
                    return []

                # 3. Extract unique image IDs
                # We want to return the parent images of these similar objects
                image_ids = []
                seen_images = set()
                for obj in object_results:
                    iid = obj['image_id']
                    if iid not in seen_images:
                        image_ids.append(iid)
                        seen_images.add(iid)
                    if len(image_ids) >= top_k:
                        break

                if not image_ids:
                    return []

                # 4. Fetch full image metadata
                placeholders = ','.join(['%s'] * len(image_ids))
                sql = f"SELECT * FROM images WHERE id IN ({placeholders})"
                params = list(image_ids)
                if PROJECT_SLUG:
                    sql += " AND project_slug = %s"
                    params.append(PROJECT_SLUG)
                cur.execute(sql, tuple(params))
                image_rows = cur.fetchall()
                
                # Sort images based on the order of their best matching object
                image_map = {r['id']: dict(r) for r in image_rows}
                results = []
                for iid in image_ids:
                    if iid in image_map:
                        results.append(image_map[iid])
                
                return results

        except Exception as e:
            print(f"Object similarity search failed: {e}")
            return []
        finally:
            conn.close()
