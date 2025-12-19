from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import os
from pathlib import Path

# Adjust path for db import if running as file
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.search import SearchEngine
from backend.db import (
    set_favorite, set_notes, create_collection, 
    add_to_collection, remove_from_collection, 
    get_all_collections, get_collection_images,
    get_db_connection, get_image_by_path
)
from backend.config import THUMBNAILS_DIR, BASE_DIR
from backend.pdf_generator import PDFGenerator
from backend.email_service import EmailService
import json
import psycopg2.extras

app = FastAPI(title="Landscape Portfolio Search")

# CORS (Allow all for local dev convenience, though same origin usually)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Search Engine (Global state)
search_engine = None

@app.on_event("startup")
def startup_event():
    global search_engine
    search_engine = SearchEngine()

# Models
class SearchRequest(BaseModel):
    query: str
    top_k: int = 50
    folder: Optional[str] = None
    favorites_only: bool = False

class SimilarSearchRequest(BaseModel):
    id: int
    top_k: int = 50

class FavoriteRequest(BaseModel):
    id: int
    favorite: bool

class NoteRequest(BaseModel):
    id: int
    notes: str

class CreateCollectionRequest(BaseModel):
    name: str

class CollectionItemRequest(BaseModel):
    collection_id: int
    image_id: int

# API
@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/search")
async def search_endpoint(req: SearchRequest):
    results = search_engine.search(req.query, req.top_k, req.favorites_only, req.folder)
    return {"results": results}

@app.post("/api/search/similar")
async def search_similar_endpoint(req: SimilarSearchRequest):
    results = search_engine.search_by_image(req.id, req.top_k)
    return {"results": results}

@app.post("/api/favorite")
def toggle_favorite(req: FavoriteRequest):
    set_favorite(req.id, req.favorite)
    return {"status": "updated", "id": req.id, "favorite": req.favorite}

@app.post("/api/notes")
def update_notes(req: NoteRequest):
    set_notes(req.id, req.notes)
    return {"status": "updated", "id": req.id, "notes": req.notes}

@app.get("/api/folders")
def get_folders():
    # Helper to get distinct folders
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT folder FROM images ORDER BY folder")
        rows = cur.fetchall()
    conn.close()
    return {"folders": [r[0] for r in rows]}

@app.get("/api/collections")
def list_collections():
    return get_all_collections()

@app.get("/api/collection/{id}")
def get_collection(id: int):
    images = get_collection_images(id)
    return {"id": id, "images": images}

@app.post("/api/collection/create")
def create_collection_endpoint(req: CreateCollectionRequest):
    cid = create_collection(req.name)
    if cid is None:
        raise HTTPException(status_code=400, detail="Collection already exists")
    return {"id": cid, "name": req.name}

@app.post("/api/collection/add")
def add_to_collection_endpoint(req: CollectionItemRequest):
    add_to_collection(req.collection_id, req.image_id)
    return {"status": "added"}

@app.post("/api/collection/remove")
def remove_from_collection_endpoint(req: CollectionItemRequest):
    remove_from_collection(req.collection_id, req.image_id)
    return {"status": "removed"}

@app.get("/api/image/{id}/raw")
def get_image_raw(id: int):
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT file_path FROM images WHERE id = %s", (id,))
        img = cur.fetchone()
    conn.close()
    
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    
    file_path = img[0]
    
    # If it's a Supabase/External URL, redirect to it
    if file_path.startswith("http"):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(file_path)
        
    # Otherwise, fallback to local file service (if any record still points local)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Local image file not found")
        
    return FileResponse(file_path)

# Models for Vision Analysis
class AnalyzeVisionRequest(BaseModel):
    image_ids: List[int]

@app.post("/api/vision/analyze")
def analyze_vision(req: AnalyzeVisionRequest):
    """Comprehensive vision board analysis with themes, patterns, and insights."""
    if not req.image_ids:
        raise HTTPException(status_code=400, detail="No images provided")
    
    from backend.vision_analyzer import get_analyzer
    analyzer = get_analyzer()
    
    try:
        analysis = analyzer.analyze_vision_board(req.image_ids)
        return analysis
    except Exception as e:
        print(f"Vision analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Legacy endpoint (kept for backwards compatibility)
class AnalyzeStyleRequest(BaseModel):
    image_ids: List[int]

@app.post("/api/analyze-style")
def analyze_style(req: AnalyzeStyleRequest):
    """Legacy style detection endpoint."""
    if not search_engine:
        raise HTTPException(status_code=503, detail="Search engine not ready")
    
    style = search_engine.analyze_board(req.image_ids)
    return {"style": style}

class ImageDetailsRequest(BaseModel):
    ids: List[int]

@app.post("/api/images/details")
def get_images_details(req: ImageDetailsRequest):
    if not req.ids:
        return {"images": []}
        
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        placeholders = ','.join(['%s'] * len(req.ids))
        query = f"SELECT id, file_path, thumbnail_path, favorite FROM images WHERE id IN ({placeholders})"
        cur.execute(query, tuple(req.ids))
        rows = cur.fetchall()
        
    conn.close()
    return {"images": [dict(r) for r in rows]}

# Lead Gen Models
class LeadRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    timeline: str
    budget: str
    address: Optional[str] = None
    image_ids: List[int]
    image_notes: Optional[dict] = {} # Map of ID -> Note String
    detected_style: Optional[str] = None

@app.post("/api/leads/submit")
def submit_lead(req: LeadRequest):
    # 1. Fetch Image Details
    selected_images = []
    # Using local helper or DB query
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        if req.image_ids:
            placeholders = ','.join(['%s'] * len(req.image_ids))
            cur.execute(f"SELECT * FROM images WHERE id IN ({placeholders})", tuple(req.image_ids))
            rows = cur.fetchall()
            # Preserve order?
            row_map = {r['id']: dict(r) for r in rows}
            for iid in req.image_ids:
                if iid in row_map:
                    img_data = row_map[iid]
                    # Inject Note if exists
                    if req.image_notes and str(iid) in req.image_notes:
                        img_data['user_note'] = req.image_notes[str(iid)]
                    selected_images.append(img_data)
    
    # 2. Vision Analytics (Mind Reader Effect)
    vision_report = {}
    if req.image_ids and search_engine:
        vision_report = search_engine.analyze_board(req.image_ids)
    
    # 3. Save Lead to DB
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO leads (name, email, phone, timeline, budget, address, vision_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                req.name, req.email, req.phone, req.timeline, req.budget, req.address, 
                json.dumps({
                    "ids": req.image_ids,
                    "notes": req.image_notes,
                    "manual_style": req.detected_style,
                    "report": vision_report
                })
            ))
            lead_id = cur.fetchone()[0]
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error saving lead: {e}")
        raise HTTPException(status_code=500, detail="Failed to save lead")
    finally:
        conn.close()

    # 3. Generate PDF
    lead_data = req.dict()
    lead_data['vision_report'] = vision_report # Inject the AI analysis
    
    pdf_gen = PDFGenerator()
    try:
        report_path = pdf_gen.generate_report(lead_data, selected_images)
    except Exception as e:
        print(f"PDF Gen Error: {e}")
        report_path = "Error generating PDF"

    # 4. Trigger Email
    email_svc = EmailService()
    email_svc.send_lead_notification(lead_data, report_path)

    return {"status": "success", "lead_id": lead_id, "report_path": report_path}

# Static Mounts
# Mount thumbnails explicitly to confirm access

app.mount("/thumbnails", StaticFiles(directory=str(THUMBNAILS_DIR)), name="thumbnails")

# Mount Frontend - MUST be last or it catches API routes if we mounted root
# Actually, better to mount static URL for assets, and "/" for index.html manually? 
# OR just mount static to "/" with html=True
STATIC_DIR = BASE_DIR / "backend/static"
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
