-- Migration: Add professional landscape design dimensions to public.images
ALTER TABLE public.images 
ADD COLUMN IF NOT EXISTS design_style text,
ADD COLUMN IF NOT EXISTS lighting_atmosphere text,
ADD COLUMN IF NOT EXISTS maintenance_level text,
ADD COLUMN IF NOT EXISTS seasonal_interest text,
ADD COLUMN IF NOT EXISTS spatial_purpose text,
ADD COLUMN IF NOT EXISTS color_palette text[];

COMMENT ON COLUMN public.images.design_style IS 'Overall design aesthetic (e.g. Modern, English Cottage, Minimalist)';
COMMENT ON COLUMN public.images.lighting_atmosphere IS 'Dominant lighting quality and mood (e.g. Dappled Sunlight, Twilight Glow)';
COMMENT ON COLUMN public.images.maintenance_level IS 'Expected care requirements (e.g. Low Maintenance, High-Touch Horticultural)';
COMMENT ON COLUMN public.images.seasonal_interest IS 'Primary peak performative seasons';
COMMENT ON COLUMN public.images.spatial_purpose IS 'Primary human function of the space (e.g. Al Fresco Dining, Private Sanctuary)';
COMMENT ON COLUMN public.images.color_palette IS 'Key color themes detected by AI';
