-- Migration: Add richer image analysis columns to public.images
ALTER TABLE public.images 
ADD COLUMN IF NOT EXISTS rich_tags text[],
ADD COLUMN IF NOT EXISTS hardscape_materials text[],
ADD COLUMN IF NOT EXISTS softscape_elements text[],
ADD COLUMN IF NOT EXISTS architectural_features text[];

COMMENT ON COLUMN public.images.rich_tags IS '20 general descriptive adjectives from AI analysis';
COMMENT ON COLUMN public.images.hardscape_materials IS 'Specific stone, wood, metal types from AI analysis';
COMMENT ON COLUMN public.images.softscape_elements IS 'Planting styles, specific tree types from AI analysis';
COMMENT ON COLUMN public.images.architectural_features IS 'Pools, pergolas, fire features from AI analysis';
