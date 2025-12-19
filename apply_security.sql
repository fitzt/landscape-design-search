-- Enable RLS for all requested tables
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE images ENABLE ROW LEVEL SECURITY;
ALTER TABLE collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE collection_items ENABLE ROW LEVEL SECURITY;

-- 1. Leads Table Policies
-- Allow anyone (anon) to insert leads
CREATE POLICY "Allow public lead submission" ON leads
FOR INSERT TO anon
WITH CHECK (true);

-- Allow only authenticated users (admins) to select or delete leads
CREATE POLICY "Allow admin access to leads" ON leads
FOR ALL TO authenticated
USING (true);

-- 2. Images Table Policies
-- Allow everyone to view images
CREATE POLICY "Allow public image view" ON images
FOR SELECT TO public
USING (true);

-- Allow only authenticated users (admins) to insert/update/delete images
CREATE POLICY "Allow admin manage images" ON images
FOR ALL TO authenticated
USING (true);

-- 3. Collections Table Policies
-- Allow everyone to view collections
CREATE POLICY "Allow public collection view" ON collections
FOR SELECT TO public
USING (true);

-- Allow only authenticated users (admins) to manage collections
CREATE POLICY "Allow admin manage collections" ON collections
FOR ALL TO authenticated
USING (true);

-- 4. Collection Items Table Policies
-- Allow everyone to view collection items
CREATE POLICY "Allow public collection item view" ON collection_items
FOR SELECT TO public
USING (true);

-- Allow only authenticated users (admins) to manage collection items
CREATE POLICY "Allow admin manage collection items" ON collection_items
FOR ALL TO authenticated
USING (true);
