-- Ensure vector extension exists
CREATE EXTENSION IF NOT EXISTS vector;

-- Create table public.image_objects to store segmented objects
CREATE TABLE IF NOT EXISTS public.image_objects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id BIGINT REFERENCES public.images(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    mask_polygon JSONB, -- Coordinates for UI overlay
    object_embedding vector(512), -- CLIP embedding for the object crop
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.image_objects ENABLE ROW LEVEL SECURITY;

-- Allow public read access
CREATE POLICY "Allow public read access"
ON public.image_objects
FOR SELECT
TO public
USING (true);

-- Allow service role full access (for the python script)
CREATE POLICY "Allow full access for service role"
ON public.image_objects
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Index for vector search on object embeddings
CREATE INDEX IF NOT EXISTS image_objects_embedding_idx ON public.image_objects 
USING ivfflat (object_embedding vector_cosine_ops)
WITH (lists = 100);

-- Index for faster joins
CREATE INDEX IF NOT EXISTS idx_image_objects_image_id ON public.image_objects(image_id);
