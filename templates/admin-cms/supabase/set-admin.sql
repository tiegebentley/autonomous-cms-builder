-- Replace the email and run in Supabase SQL editor to promote the first admin.
-- Requires the user to have already signed up at least once (so a profile row exists).
UPDATE public.profiles
SET is_admin = true
WHERE email = 'REPLACE_WITH_CLIENT_EMAIL@example.com';
