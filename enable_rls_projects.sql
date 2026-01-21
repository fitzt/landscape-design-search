-- Enable RLS on public.projects to secure it
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

-- Allow public read access to everyone (anon and authenticated)
CREATE POLICY "Allow public read access"
ON public.projects
FOR SELECT
TO public
USING (true);
