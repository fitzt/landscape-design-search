-- Add project_slug to leads
ALTER TABLE leads ADD COLUMN IF NOT EXISTS project_slug TEXT;

-- Add project_slug to collections
ALTER TABLE collections ADD COLUMN IF NOT EXISTS project_slug TEXT;

-- Update existing records to 'lynch' as default (assuming most existing data is Lynch)
-- Or leave NULL and handle it in the application logic. 
-- For now, let's keep them as is and the app will filter by PROJECT_SLUG if set.
