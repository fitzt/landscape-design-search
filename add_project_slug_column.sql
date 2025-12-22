-- Add project_slug column if it doesn't exist
ALTER TABLE public.images ADD COLUMN IF NOT EXISTS project_slug TEXT;

-- Index for fast exact matching in Project Mode
CREATE INDEX IF NOT EXISTS idx_images_project_slug ON public.images(project_slug);
