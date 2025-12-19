import os
import glob
import psycopg2
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # This is actually the anon key
db_url: str = os.environ.get("DATABASE_URL")

if not url or not key or not db_url:
    print("Error: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, or DATABASE_URL not set in .env")
    exit(1)

BUCKET_NAME = "portfolio-images"

def setup_storage_via_sql():
    """Create bucket and set policies via direct SQL connection."""
    print("Setting up storage bucket and policies via SQL...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        # 1. Ensure bucket exists
        cur.execute(f"INSERT INTO storage.buckets (id, name, public) VALUES ('{BUCKET_NAME}', '{BUCKET_NAME}', true) ON CONFLICT (id) DO NOTHING")
        
        # 2. Add policies to allow anonymous uploads for migration
        # We delete existing migration policies first to avoid duplicates
        cur.execute(f"DELETE FROM storage.objects WHERE bucket_id = '{BUCKET_NAME}'") # Clean start if needed
        
        # Allow anyone to upload to this bucket
        cur.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow anonymous uploads of portfolio images') THEN
                    CREATE POLICY "Allow anonymous uploads of portfolio images" ON storage.objects
                    FOR INSERT TO public
                    WITH CHECK (bucket_id = '{BUCKET_NAME}');
                END IF;
                
                IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow anonymous read of portfolio images') THEN
                    CREATE POLICY "Allow anonymous read of portfolio images" ON storage.objects
                    FOR SELECT TO public
                    USING (bucket_id = '{BUCKET_NAME}');
                END IF;
            END
            $$;
        """)
        
        conn.close()
        print("Storage setup complete.")
        return True
    except Exception as e:
        print(f"SQL Storage Setup Error: {e}")
        return False

def migrate_images():
    supabase: Client = create_client(url, key)

    # local images
    local_dir = "/Users/thomasfitzgerald/landscape-design-search/optimized_images"
    image_files = glob.glob(os.path.join(local_dir, "*"))
    print(f"Found {len(image_files)} local images to upload.")

    # Database connection for patching
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    count = 0
    errors = 0
    first_url = None

    for file_path in image_files:
        filename = os.path.basename(file_path)
        
        try:
            # Upload to Supabase Storage
            with open(file_path, 'rb') as f:
                supabase.storage.from_(BUCKET_NAME).upload(
                    path=filename,
                    file=f.read(),
                    file_options={"cache-control": "3600", "upsert": "true"}
                )
            
            # Construct Public URL
            public_url = f"{url}/storage/v1/object/public/{BUCKET_NAME}/{filename}"
            
            if first_url is None:
                first_url = public_url

            # Patch Database
            cur.execute("""
                UPDATE images 
                SET file_path = %s
                WHERE file_path = %s OR filename = %s
            """, (public_url, file_path, filename))
            
            count += 1
            if count % 50 == 0:
                print(f"Uploaded and patched {count} images...")
                conn.commit()

        except Exception as e:
            # Log specific error to help debug
            # print(f"Error migrating {filename}: {e}")
            errors += 1

    conn.commit()
    conn.close()

    print("="*60)
    print(f"Migration finished. Success: {count}, Errors: {errors}")
    if first_url:
        print(f"Sample URL: {first_url}")
    print("="*60)

if __name__ == "__main__":
    if setup_storage_via_sql():
        migrate_images()
