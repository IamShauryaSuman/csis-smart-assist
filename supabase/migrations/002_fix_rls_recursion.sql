-- Drop the policies that cause infinite recursion
DROP POLICY IF EXISTS "Admins can view all profiles" ON public.profiles;
DROP POLICY IF EXISTS "Admins can manage all bookings" ON public.bookings;
DROP POLICY IF EXISTS "Admins can manage rag_files" ON public.rag_files;
DROP POLICY IF EXISTS "Admins can manage rag_chunks" ON public.rag_chunks;

-- Create a security definer function to bypass RLS when checking admin status
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT COALESCE(
    (SELECT is_admin FROM public.profiles WHERE id = auth.uid()),
    FALSE
  );
$$;

-- Recreate the policies using the new function
CREATE POLICY "Admins can view all profiles"
    ON public.profiles FOR SELECT USING ( public.is_admin() );

CREATE POLICY "Admins can manage all bookings"
    ON public.bookings FOR ALL USING ( public.is_admin() );

CREATE POLICY "Admins can manage rag_files"
    ON public.rag_files FOR ALL USING ( public.is_admin() );

CREATE POLICY "Admins can manage rag_chunks"
    ON public.rag_chunks FOR ALL USING ( public.is_admin() );
