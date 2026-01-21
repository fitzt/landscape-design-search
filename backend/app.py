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

from backend.search_strategies.coordinator import StrategyCoordinator
from backend.db import (
    set_favorite, set_notes, create_collection, 
    add_to_collection, remove_from_collection, 
    get_all_collections, get_collection_images,
    get_db_connection, get_image_by_path
)
from backend.config import DB_PATH, THUMBNAILS_DIR, DEFAULT_TOP_K, PROJECT_SLUG, PHOTO_FOLDER, BASE_DIR
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

# Initialize Strategy Coordinator (Global state)
strategy_coordinator = None

@app.on_event("startup")
def startup_event():
    global strategy_coordinator
    strategy_coordinator = StrategyCoordinator()

# Models
class SearchRequest(BaseModel):
    query: str
    top_k: int = 50
    folder: Optional[str] = None
    slug: Optional[str] = None
    favorites_only: bool = False

class SimilarSearchRequest(BaseModel):
    id: int
    top_k: int = 50

class ObjectSearchRequest(BaseModel):
    object_id: str
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
    search_data = strategy_coordinator.search(req.query, req.top_k, req.favorites_only, req.folder, req.slug)
    
    if isinstance(search_data, dict):
        return {
            "results": search_data.get("results", []),
            "trust_header": search_data.get("trust_header")
        }
    
    return {"results": search_data}

@app.get("/api/projects/{slug}")
async def get_project_metadata(slug: str):
    if PROJECT_SLUG and slug != PROJECT_SLUG:
        raise HTTPException(status_code=403, detail="Access denied to this project")
        
    conn = get_db_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM projects WHERE filename_slug = %s", (slug,))
        row = cur.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return dict(row)

@app.post("/api/similar")
async def similar_endpoint(req: SimilarSearchRequest):
    results = strategy_coordinator.search_by_image(req.id, req.top_k)
    return {"results": results}

@app.post("/api/similar-object")
async def object_search_endpoint(req: ObjectSearchRequest):
    results = strategy_coordinator.search_by_object(req.object_id, req.top_k)
    return {"results": results}

@app.get("/api/images/{image_id}/objects")
async def get_image_objects(image_id: int):
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # 1. Fetch image dimensions for scaling (with safety check)
        sql = "SELECT width, height FROM images WHERE id = %s"
        params = [image_id]
        if PROJECT_SLUG:
            sql += " AND project_slug = %s"
            params.append(PROJECT_SLUG)
        cur.execute(sql, tuple(params))
        img_row = cur.fetchone()
        
        if not img_row:
            return {"width": 1024, "height": 1024, "data": []}
        
        # 2. Fetch objects with high confidence
        cur.execute("""
            SELECT io.id, io.label, io.confidence, io.mask_polygon
            FROM image_objects io
            JOIN images i ON io.image_id = i.id
            WHERE io.image_id = %s AND io.confidence > 0.6
        """ + (f" AND i.project_slug = '{PROJECT_SLUG}'" if PROJECT_SLUG else "") + """
            ORDER BY io.confidence DESC
        """, (image_id,))
        rows = cur.fetchall()
        
        objects = []
        for row in rows:
            objects.append({
                "id": str(row['id']),
                "label": row['label'],
                "confidence": row['confidence'],
                "mask_polygon": row['mask_polygon']
            })
            
        return {
            "width": img_row['width'] if img_row else 1024,
            "height": img_row['height'] if img_row else 1024,
            "data": objects
        }
    except Exception as e:
        print(f"Error fetching objects: {e}")
        return {"width": 1024, "height": 1024, "data": []}
    finally:
        conn.close()

@app.post("/api/images/{image_id}/refine")
async def refine_image_analysis(image_id: int):
    """
    Triggers a deep re-analysis of an image:
    1. Global GPT-4o Vision scan for rich tags and materials.
    2. Local SAM/CLIP scan for specific object polygons with expanded vocabulary.
    """
    import subprocess
    import os
    
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT file_path FROM images WHERE id = %s", (image_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Image not found")
        
        file_path = row['file_path']
        
        # 1. Run Global Enrichment (GPT-4o)
        # We'll use a simplified version of enrich_images.py logic or call it as a script
        # For speed and isolation, we'll try running the script via subprocess as it's already set up
        # However, enrich_images.py processes ALL images. We need a targeted version.
        # Let's import the logic instead if possible, or just use a small subprocess command.
        
        # NOTE: For this implementation, we will assume enrich_images.py and process_objects_m3.py 
        # can be modified to take a specific image_id, OR we just trigger them and they find the work.
        # But to be precise for the user, let's run a targeted script.
        
        print(f"Triggering refinement for image {image_id}")
        
        # Run Object Process (Spatial)
        # We modify process_objects_m3.py slightly to handle a single ID if passed?
        # For now, we'll just run them and they will pick up images that need work.
        # More robust: run a small python snippet that processes THIS specific image.
        
        refine_cmd = f"PYTHONPATH=. python3 -c \"from process_objects_m3 import process_image; process_image({image_id}, '{file_path}')\""
        subprocess.run(refine_cmd, shell=True, check=True)
        
        # Run Global Enrichment (Global)
        # Assuming enrich_images.py has a targeted function
        enrich_cmd = f"PYTHONPATH=. python3 -c \"import asyncio; from enrich_images import enrich_image; asyncio.run(enrich_image({image_id}, '{file_path}'))\""
        subprocess.run(enrich_cmd, shell=True, check=True)
        
        return {"status": "success", "message": "Refinement complete"}
    except Exception as e:
        print(f"Refinement failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# Keep legacy endpoint for now to avoid breaking existing frontend if it hasn't refreshed
@app.get("/api/image-objects/{image_id}")
async def get_image_objects_legacy(image_id: int):
    res = await get_image_objects(image_id)
    return {"objects": res["data"]}

@app.post("/api/favorite")
def toggle_favorite(req: FavoriteRequest):
    set_favorite(req.id, req.favorite)
    return {"status": "updated", "id": req.id, "favorite": req.favorite}

@app.post("/api/notes")
def update_notes(req: NoteRequest):
    set_notes(req.id, req.notes)
    return {"status": "updated", "id": req.id, "notes": req.notes}

@app.post("/api/analyze-board")
async def analyze_board(req: List[int]):
    report = strategy_coordinator.analyze_board(req)
    return report

@app.get("/api/folders")
def get_folders():
    # Helper to get distinct folders
    conn = get_db_connection()
    with conn.cursor() as cur:
        sql = "SELECT DISTINCT folder FROM images"
        if PROJECT_SLUG:
            sql += f" WHERE project_slug = '{PROJECT_SLUG}'"
        sql += " ORDER BY folder"
        cur.execute(sql)
        rows = cur.fetchall()
    conn.close()
    return {"folders": [r[0] for r in rows]}

@app.get("/api/collections")
def list_collections():
    return get_all_collections()

@app.get("/api/collection/{id}")
def get_collection(id: int):
    images = get_collection_images(id)
    if not images and PROJECT_SLUG:
        # Check if collection exists but belongs to another project
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT project_slug FROM collections WHERE id = %s", (id,))
            row = cur.fetchone()
        conn.close()
        if row and row[0] != PROJECT_SLUG:
             raise HTTPException(status_code=403, detail="Access denied to this collection")
             
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
        sql = "SELECT file_path FROM images WHERE id = %s"
        params = [id]
        if PROJECT_SLUG:
            sql += " AND project_slug = %s"
            params.append(PROJECT_SLUG)
        cur.execute(sql, tuple(params))
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
        query = f"""
            SELECT id, file_path, thumbnail_path, favorite, tags, style_scores, caption,
                   design_style, maintenance_level, seasonal_interest, spatial_purpose, color_palette, project_slug,
                   privacy_level, terrain_type, hardscape_ratio, material_palette, architectural_features
            FROM images 
            WHERE id IN ({placeholders})
        """
        if PROJECT_SLUG:
            query += " AND project_slug = %s"
            cur.execute(query, tuple(req.ids + [PROJECT_SLUG]))
        else:
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
                INSERT INTO leads (name, email, phone, timeline, budget, address, vision_json, project_slug)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                req.name, req.email, req.phone, req.timeline, req.budget, req.address, 
                json.dumps({
                    "ids": req.image_ids,
                    "notes": req.image_notes,
                    "manual_style": req.detected_style,
                    "report": vision_report
                }),
                PROJECT_SLUG
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
app.mount("/images", StaticFiles(directory=str(PHOTO_FOLDER)), name="images")

# Mount Frontend - MUST be last or it catches API routes if we mounted root
# Actually, better to mount static URL for assets, and "/" for index.html manually? 
# OR just mount static to "/" with html=True
STATIC_DIR = BASE_DIR / "backend/static"
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.app:app", host="0.0.0.0", port=port, reload=True)
