CREATE TABLE IF NOT EXISTS public.{{TABLE_NAME}} (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  {{COLUMNS_BLOCK}},
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS {{TABLE_NAME}}_{{ORDER_BY}}_idx
  ON public.{{TABLE_NAME}} ({{ORDER_BY}});

ALTER TABLE public.{{TABLE_NAME}} ENABLE ROW LEVEL SECURITY;

-- Public read — content is shown on the marketing site to anonymous visitors.
DROP POLICY IF EXISTS "{{TABLE_NAME}}_select_public" ON public.{{TABLE_NAME}};
CREATE POLICY "{{TABLE_NAME}}_select_public"
  ON public.{{TABLE_NAME}} FOR SELECT
  USING (true);

-- Admin-only writes (insert / update / delete).
DROP POLICY IF EXISTS "{{TABLE_NAME}}_insert_admin" ON public.{{TABLE_NAME}};
CREATE POLICY "{{TABLE_NAME}}_insert_admin"
  ON public.{{TABLE_NAME}} FOR INSERT
  WITH CHECK ((SELECT is_admin FROM public.profiles WHERE id = auth.uid()) = true);

DROP POLICY IF EXISTS "{{TABLE_NAME}}_update_admin" ON public.{{TABLE_NAME}};
CREATE POLICY "{{TABLE_NAME}}_update_admin"
  ON public.{{TABLE_NAME}} FOR UPDATE
  USING ((SELECT is_admin FROM public.profiles WHERE id = auth.uid()) = true);

DROP POLICY IF EXISTS "{{TABLE_NAME}}_delete_admin" ON public.{{TABLE_NAME}};
CREATE POLICY "{{TABLE_NAME}}_delete_admin"
  ON public.{{TABLE_NAME}} FOR DELETE
  USING ((SELECT is_admin FROM public.profiles WHERE id = auth.uid()) = true);

-- Touch updated_at on any UPDATE.
CREATE OR REPLACE FUNCTION public.touch_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS {{TABLE_NAME}}_touch_updated_at ON public.{{TABLE_NAME}};
CREATE TRIGGER {{TABLE_NAME}}_touch_updated_at
  BEFORE UPDATE ON public.{{TABLE_NAME}}
  FOR EACH ROW EXECUTE FUNCTION public.touch_updated_at();
