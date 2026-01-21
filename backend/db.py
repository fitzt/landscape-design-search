import os
import psycopg2
import psycopg2.extras
from datetime import datetime
from dotenv import load_dotenv

# Import config for PROJECT_SLUG
from backend.config import PROJECT_SLUG

# Load env in case it's not loaded (e.g. running script directly)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set")
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Images table
    # SERIAL replaces AUTOINCREMENT
    # TIMESTAMP DEFAULT CURRENT_TIMESTAMP works in Postgres
    # BOOLEAN DEFAULT FALSE
    c.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id SERIAL PRIMARY KEY,
            file_path TEXT UNIQUE NOT NULL,
            filename TEXT,
            folder TEXT,
            mtime REAL,
            file_hash TEXT,
            exif_date TEXT,
            width INTEGER,
            height INTEGER,
            thumbnail_path TEXT,
            favorite BOOLEAN DEFAULT FALSE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Collections table
    c.execute('''
        CREATE TABLE IF NOT EXISTS collections (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Collection items (many-to-many)
    c.execute('''
        CREATE TABLE IF NOT EXISTS collection_items (
            collection_id INTEGER,
            image_id INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (collection_id, image_id),
            FOREIGN KEY(collection_id) REFERENCES collections(id) ON DELETE CASCADE,
            FOREIGN KEY(image_id) REFERENCES images(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

def get_image_by_path(file_path):
    conn = get_db_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    sql = 'SELECT * FROM images WHERE file_path = %s'
    params = [file_path]
    if PROJECT_SLUG:
        sql += " AND project_slug = %s"
        params.append(PROJECT_SLUG)
    c.execute(sql, tuple(params))
    img = c.fetchone()
    conn.close()
    return dict(img) if img else None

def upsert_image(metadata):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if exists
    c.execute('SELECT id FROM images WHERE file_path = %s', (metadata['file_path'],))
    existing = c.fetchone()
    
    if existing:
        # Update
        img_id = existing[0]
        c.execute('''
            UPDATE images SET 
                mtime = %s, file_hash = %s, exif_date = %s, width = %s, height = %s, thumbnail_path = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (
            metadata['mtime'], metadata['file_hash'], metadata.get('exif_date'), 
            metadata['width'], metadata['height'], metadata['thumbnail_path'], 
            img_id
        ))
    else:
        # Insert
        c.execute('''
            INSERT INTO images (file_path, filename, folder, mtime, file_hash, exif_date, width, height, thumbnail_path, project_slug)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (
            metadata['file_path'], metadata['filename'], metadata['folder'], 
            metadata['mtime'], metadata['file_hash'], metadata.get('exif_date'), 
            metadata['width'], metadata['height'], metadata['thumbnail_path'],
            PROJECT_SLUG
        ))
        img_id = c.fetchone()[0]
        
    conn.commit()
    conn.close()
    return img_id

def set_favorite(image_id, is_favorite):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE images SET favorite = %s WHERE id = %s', (is_favorite, image_id))
    conn.commit()
    conn.close()

def set_notes(image_id, notes):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE images SET notes = %s WHERE id = %s', (notes, image_id))
    conn.commit()
    conn.close()

def create_collection(name):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO collections (name, project_slug) VALUES (%s, %s) RETURNING id', (name, PROJECT_SLUG))
        cid = c.fetchone()[0]
        conn.commit()
        return cid
    except psycopg2.IntegrityError:
        conn.rollback()
        return None # Already exists
    finally:
        conn.close()

def add_to_collection(collection_id, image_id):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO collection_items (collection_id, image_id) VALUES (%s, %s)', (collection_id, image_id))
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
        pass # Already in collection
    finally:
        conn.close()

def remove_from_collection(collection_id, image_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM collection_items WHERE collection_id = %s AND image_id = %s', (collection_id, image_id))
    conn.commit()
    conn.close()

def get_all_collections():
    conn = get_db_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    sql = 'SELECT * FROM collections'
    params = []
    if PROJECT_SLUG:
        sql += ' WHERE project_slug = %s'
        params.append(PROJECT_SLUG)
    sql += ' ORDER BY name'
    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_collection_images(collection_id):
    conn = get_db_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    sql = '''
        SELECT i.* FROM images i
        JOIN collection_items ci ON i.id = ci.image_id
        JOIN collections coll ON ci.collection_id = coll.id
        WHERE ci.collection_id = %s
    '''
    params = [collection_id]
    if PROJECT_SLUG:
        sql += " AND coll.project_slug = %s"
        params.append(PROJECT_SLUG)
    c.execute(sql, tuple(params))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Helper to get all images for incremental check
def get_all_images_map():
    """Returns a dict of file_path -> {id, mtime, file_hash}"""
    conn = get_db_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    sql = 'SELECT id, file_path, mtime, file_hash FROM images'
    params = []
    if PROJECT_SLUG:
        sql += " WHERE project_slug = %s"
        params.append(PROJECT_SLUG)
    c.execute(sql, tuple(params))
    rows = c.fetchall()
    conn.close()
    return {r['file_path']: dict(r) for r in rows}

def delete_image(image_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM images WHERE id = %s', (image_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized (PostgreSQL).")
