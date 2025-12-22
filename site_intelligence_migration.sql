-- Migration to add Site Intelligence columns for sales qualification
ALTER TABLE public.images 
ADD COLUMN IF NOT EXISTS privacy_level TEXT,
ADD COLUMN IF NOT EXISTS terrain_type TEXT,
ADD COLUMN IF NOT EXISTS hardscape_ratio TEXT,
ADD COLUMN IF NOT EXISTS material_palette TEXT[];

-- Create indices for performance on these new attributes
CREATE INDEX IF NOT EXISTS idx_images_privacy_level ON public.images (privacy_level);
CREATE INDEX IF NOT EXISTS idx_images_terrain_type ON public.images (terrain_type);
CREATE INDEX IF NOT EXISTS idx_images_hardscape_ratio ON public.images (hardscape_ratio);
-- Material palette is an array, we can use GIN if needed for containment queries later
CREATE INDEX IF NOT EXISTS idx_images_material_palette ON public.images USING GIN (material_palette);
