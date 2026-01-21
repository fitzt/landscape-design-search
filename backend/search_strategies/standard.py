import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from ..config import INDEX_PATH, CLIP_MODEL_NAME, DEFAULT_TOP_K, PROJECT_SLUG
from ..db import get_db_connection
import psycopg2.extras
from PIL import Image
import os
from .interface import SearchInterface
from typing import List, Dict, Any, Optional

class StandardSearch(SearchInterface):
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

        # CASE 2: Query Present
        print(f"Executing semantic search for: '{query}'")
        text_emb = self.model.encode([query]).astype('float32')
        faiss.normalize_L2(text_emb)
        
        search_k = max(top_k * 20, 2000)
        D, I = self.index.search(text_emb, search_k)
        
        found_ids = [int(id) for id in I[0] if id != -1]
        scores = {int(id): float(score) for id, score in zip(I[0], D[0]) if id != -1}
        
        semantic_results = []
        if found_ids:
            placeholders = ','.join(['%s'] * len(found_ids))
            sql = f"SELECT * FROM images WHERE id IN ({placeholders})"
            params = list(found_ids)
            
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(sql, params)
                    semantic_results = [dict(r) for r in cur.fetchall()]

        keyword_results = []
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
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

        final_map = {}
        for img in semantic_results:
            if project_slug and img.get('project_slug') != project_slug: continue
            img['similarity'] = scores.get(img['id'], 0)
            if img['similarity'] < 0.25: continue
            final_map[img['id']] = img

        for img in keyword_results:
            if img['id'] in final_map:
                final_map[img['id']]['similarity'] += 0.5 
            else:
                img['similarity'] = 0.45 
                final_map[img['id']] = img
        
        results = list(final_map.values())
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]

    def search_by_image(self, image_id: int, top_k: int = DEFAULT_TOP_K):
        if not self.index or not self.model:
            return []

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

        if not row: return []
        
        file_path, anchor_folder = row
        
        if file_path.startswith("http"):
            import requests
            from io import BytesIO
            try:
                response = requests.get(file_path)
                image = Image.open(BytesIO(response.content))
            except: return []
        else:
            if not os.path.exists(file_path): return []
            try: image = Image.open(file_path)
            except: return []

        img_emb = self.model.encode([image])
        img_emb = img_emb.astype('float32')
        faiss.normalize_L2(img_emb)

        search_k = top_k * 4
        distances, ids = self.index.search(img_emb, search_k)
        
        valid_ids = [int(i) for i in ids[0] if i >= 0]
        if not valid_ids: return []

        conn = get_db_connection()
        placeholders = ','.join(['%s'] * len(valid_ids))
        query_sql = f"SELECT * FROM images WHERE id IN ({placeholders})"
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(query_sql, tuple(valid_ids))
            rows = cur.fetchall()
        conn.close()

        row_map = {r['id']: dict(r) for r in rows}
        candidates = []
        for score, img_id in zip(distances[0], ids[0]):
            if img_id < 0 or img_id == image_id or img_id not in row_map: continue
            img = row_map[img_id]
            if PROJECT_SLUG and img.get('project_slug') != PROJECT_SLUG: continue
            base_score = float(score)
            if anchor_folder and img['folder'] == anchor_folder:
                 base_score += 0.08
            img['score'] = base_score
            candidates.append(img)
            
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:top_k]

    def search_by_object(self, object_id: str, top_k: int = DEFAULT_TOP_K):
        conn = get_db_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
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
                if not row: return []
                anchor_emb = row['object_embedding']

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
                if not object_results: return []

                image_ids = []
                seen_images = set()
                for obj in object_results:
                    iid = obj['image_id']
                    if iid not in seen_images:
                        image_ids.append(iid)
                        seen_images.add(iid)
                    if len(image_ids) >= top_k: break

                if not image_ids: return []

                placeholders = ','.join(['%s'] * len(image_ids))
                sql = f"SELECT * FROM images WHERE id IN ({placeholders})"
                params = list(image_ids)
                if PROJECT_SLUG:
                    sql += " AND project_slug = %s"
                    params.append(PROJECT_SLUG)
                cur.execute(sql, tuple(params))
                image_rows = cur.fetchall()
                
                image_map = {r['id']: dict(r) for r in image_rows}
                results = []
                for iid in image_ids:
                    if iid in image_map:
                        results.append(image_map[iid])
                return results
        except: return []
        finally: conn.close()

    def analyze_board(self, image_ids: List[int]):
        from sentence_transformers import util
        import torch
        if not self.model or not image_ids: return {}
        try:
            categories = {
                "Style": ["Modern Minimalist", "Rustic Organic", "Traditional Formal", "Cottage Garden", "Luxury Resort"],
                "Material": ["Natural Stone", "Concrete Pavers", "Wood Decking", "Brick", "Gravel"],
                "Atmosphere": ["Warm & Cozy", "Cool & Sleek", "Bright & Airy", "Moody & Dramatic"]
            }
            limit_ids = image_ids[:5] 
            conn = get_db_connection()
            placeholders = ','.join(['%s'] * len(limit_ids))
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
                    try: images.append(Image.open(r[0]))
                    except: pass
            
            if not images: return {"error": "No valid images"}
            img_embs = self.model.encode(images)
            mean_emb = np.mean(img_embs, axis=0)
            report = {}
            for cat, options in categories.items():
                opt_embs = self.model.encode(options)
                sims = util.cos_sim(mean_emb, opt_embs)[0]
                best_idx = int(np.argmax(sims))
                report[cat] = options[best_idx]
            return report
        except: return {"error": "Analysis failed"}
