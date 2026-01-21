# Landscape Portfolio Search

A local-first, offline-capable implementation of a semantic image search engine.

## Prerequisites
- Python 3.11+
- A folder of images (configured in `backend/config.py` or via env var `PHOTO_FOLDER`).

## Setup

### 1. Create a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Indexer
This scans your photos, creates thumbnails, and builds the CLIP embeddings index.
It may take a while on the first run (downloading model ~300MB, processing images).

```bash
# Basic run (uses default configured folder)
python3 backend/indexer.py

# Force re-index of all files
python3 backend/indexer.py --reindex
```

### 4. Run the Server
Starts the web application at http://localhost:8000.

```bash
uvicorn backend.app:app --reload
```

## Usage
1. Openhttp://localhost:8000  in your browser.
2. Type a query like "pool landscaping lighting".
3. Use filters to narrow down by folder or favorites.
4. Click an image to view details, add notes, or add to a collection.

## Architecture
- **Backend**: FastAPI
- **Database**: SQLite (metadata, collections, favorites)
- **Search**: FAISS (vector similarity), SentenceTransformers (CLIP model)
- **Frontend**: Vanilla JS, HTML, CSS (No build step required)
