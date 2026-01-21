from .interface import SearchInterface
from typing import List, Dict, Any, Optional
import uuid
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from ..config import INDEX_PATH, CLIP_MODEL_NAME, DEFAULT_TOP_K
from ..db import get_db_connection
import psycopg2.extras
from ..consultation_engine import ConsultationEngine

class ConsultationSearch(SearchInterface):
    def __init__(self):
        self.model = None
        self.index = None
        self.engine = ConsultationEngine()
        self.load_resources()

    def load_resources(self):
        if INDEX_PATH.exists():
            print(f"Loading Consultation index from {INDEX_PATH}")
            self.index = faiss.read_index(str(INDEX_PATH))
        
        print(f"Loading CLIP model: {CLIP_MODEL_NAME}...")
        self.model = SentenceTransformer(CLIP_MODEL_NAME)
        print("Model loaded.")

    def search(self, query: str, top_k: int = 20, favorites_only: bool = False, folder: str = None, project_slug: str = None):
        if not query:
            return self._get_recent_projects(top_k)

        query_terms = query.split()
        user_city = self._extract_city(query)
        
        # 1. Generate Trust Header
        trust_header = self.engine.generate_trust_header(query_terms, user_city)

        # 2. Semantic Search (Only matching "After" images)
        text_emb = self.model.encode([query]).astype('float32')
        faiss.normalize_L2(text_emb)
        D, I = self.index.search(text_emb, 1000)
        
        found_ids = [int(id) for id in I[0] if id != -1]
        scores = {int(id): float(score) for id, score in zip(I[0], D[0]) if id != -1}
        
        if not found_ids:
            return {
                "results": self._get_knowledge_content(query_terms, user_city),
                "trust_header": trust_header
            }

        # 3. Fetch and Group into Containers
        placeholders = ','.join(['%s'] * len(found_ids))
        sql = f"SELECT * FROM images WHERE id IN ({placeholders}) AND phase = 'after' AND project_slug = 'leahy'"
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(sql, list(found_ids))
                after_images = [dict(r) for r in cur.fetchall()]

        # High confidence threshold
        is_low_confidence = not after_images or max(scores.values()) < 0.23

        if is_low_confidence:
             return {
                 "results": self._get_knowledge_content(query_terms, user_city),
                 "trust_header": trust_header
             }

        # 4. Group by project_container_id
        projects = {}
        for img in after_images:
            pid = img.get('project_container_id') or f"temp_{img['id']}"
            if pid not in projects:
                projects[pid] = {
                    "id": pid,
                    "hero_image": img,
                    "assets": {"after": [img], "context": []},
                    "description": img.get('notes', ''),
                    "location": img.get('location', 'Massachusetts'),
                    "score": scores.get(img['id'], 0)
                }
            else:
                projects[pid]["assets"]["after"].append(img)
                projects[pid]["score"] = max(projects[pid]["score"], scores.get(img['id'], 0))

        # 5. Fetch 'context'
        project_ids = [pid for pid in projects.keys() if not pid.startswith("temp_")]
        if project_ids:
            placeholders = ','.join(['%s'] * len(project_ids))
            sql = f"SELECT * FROM images WHERE project_container_id IN ({placeholders}) AND phase IN ('before', 'during')"
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(sql, project_ids)
                    context_images = cur.fetchall()
                    for c_img in context_images:
                        projects[c_img['project_container_id']]["assets"]["context"].append(dict(c_img))

        results = list(projects.values())
        results.sort(key=lambda x: x['score'], reverse=True)
        final_results = results[:top_k]

        # 5. Proactive Knowledge Injection (Narrative Bridge)
        knowledge_card = self.engine.get_knowledge_card(query_terms, user_city or "the North Shore")
        if knowledge_card:
            # Inject at position 1 (after the first result) for maximum impact
            insert_pos = min(1, len(final_results))
            final_results.insert(insert_pos, knowledge_card)

        return {
            "results": final_results,
            "trust_header": trust_header
        }

    def _extract_city(self, query):
        cities = self.engine.profile['service_area']
        for city in cities:
            if city.lower() in query.lower():
                return city
        return None

    def _get_knowledge_content(self, query_terms, user_city):
        knowledge_card = self.engine.get_knowledge_card(query_terms, user_city or "the North Shore")
        if knowledge_card:
            return [knowledge_card]
        
        # Fallback to general expertise if no triggers match
        return [{
            "type": "knowledge_card",
            "title": "Coastal Experts",
            "fact": "New England coastal projects require specialized knowledge of salt-tolerant plantings and freeze-thaw masonry.",
            "local_context": f"Our team has maintained high standards in {user_city or 'the North Shore'} since 1984.",
            "visual_tags": ["granite", "stone"]
        }]

    def _get_recent_projects(self, top_k):
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("SELECT * FROM images WHERE project_slug = 'leahy' AND phase = 'after' LIMIT %s", (top_k,))
                rows = cur.fetchall()
        
        results = []
        for r in rows:
            results.append({
                "id": r['project_container_id'] or str(uuid.uuid4()),
                "hero_image": dict(r),
                "assets": {"after": [dict(r)], "context": []},
                "description": r['notes'],
                "location": "Massachusetts"
            })
        return {"results": results, "trust_header": f"Serving {self.engine.profile['hq_city']} and the North Shore since {self.engine.profile['founded']}."}

    def search_by_image(self, image_id: int, top_k: int = 20): return []
    def search_by_object(self, object_id: str, top_k: int = 20): return []
    def analyze_board(self, image_ids: List[int]): return {}
