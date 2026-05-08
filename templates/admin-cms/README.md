# admin-cms template

Reusable scaffolding the autonomous-cms-builder stamps into a Higgsfield-generated
client site to give the client a Supabase-backed admin CMS.

Modeled after `/root/small-group-soccer-project/app/src/pages/admin/` — same
patterns, generalized.

## Layout

```
shell/                       Verbatim files copied into client repo
  AdminRoute.tsx               auth gate (checks profiles.is_admin)
  AdminNav.tsx                 nav bar; consumes a builder-generated items array
  AdminLayout.tsx              one-line wrapper combining the two
  supabase.ts                  Supabase client (reads VITE_SUPABASE_* envs)

manage-page-template/        Stamped once per detected content type
  Manage__ENTITY_PASCAL__.tsx.tpl   parameterized CRUD page
  _form-fragments.md                field-type → form snippet lookup

supabase/                    SQL the builder runs against the client's project
  000_profiles_and_admin.sql        ALWAYS run first (auth + profiles table)
  set-admin.sql                     promote first admin (manual paste)
  _content_table_template.sql       stamped once per detected content type
```

## What stays verbatim vs what gets parameterized

**Verbatim** (copied as-is into the client repo):
- `shell/AdminRoute.tsx`
- `shell/AdminLayout.tsx`
- `shell/supabase.ts`
- `supabase/000_profiles_and_admin.sql`

**Parameterized** (placeholders substituted per content type):
- `shell/AdminNav.tsx` — the `items` array is generated, but the file itself
  is identical in every client repo.
- `manage-page-template/Manage__ENTITY_PASCAL__.tsx.tpl` — one stamped file
  per detected content type.
- `supabase/_content_table_template.sql` — one stamped migration per content
  type.

## Builder flow (next session — not implemented yet)

1. Scan the Higgsfield-generated site (HTML/JSX) → list of inferred content
   types, each with `{ entity, table_name, fields[] }`.
2. Apply `supabase/000_profiles_and_admin.sql` to the client's Supabase project.
3. For each content type, stamp `_content_table_template.sql` and apply.
4. Copy `shell/AdminRoute.tsx`, `AdminLayout.tsx`, `supabase.ts` verbatim.
5. Generate the `ADMIN_NAV_ITEMS` constant and copy `AdminNav.tsx`.
6. For each content type, stamp `Manage__ENTITY_PASCAL__.tsx.tpl`. The form
   body is built by concatenating `_form-fragments.md` snippets per field type.
7. Patch the client's `App.tsx` to mount the `/admin/*` route subtree wrapped
   in `<AdminLayout navItems={ADMIN_NAV_ITEMS}>`.
8. Patch the client's frontend pages to fetch from Supabase instead of the
   hardcoded data files Higgsfield emits.

## Required client-repo dependencies

The template assumes the client repo already has (Higgsfield should give us
most of these — verify per template):

- `react`, `react-dom`, `react-router-dom`
- `@supabase/supabase-js`
- `lucide-react`
- shadcn/ui primitives at `@/components/ui/{button,input,textarea,dialog}`
- `@/hooks/use-toast` (shadcn)
- Vite-style `import.meta.env` for `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`

If a Higgsfield site is missing any of these, the builder needs to add them
before stamping the template — track this in the builder agent's prerequisites
check.

## Tenancy

Per-client Supabase project (decided 2026-05-08). No `tenant_id` columns
anywhere. Each client repo gets its own `.env.local` with their project's
URL + anon key.

## Source provenance

- `shell/AdminRoute.tsx` — adapted from `small-group-soccer-project/app/src/components/AdminRoute.tsx`
- `shell/AdminNav.tsx` — generalized from same project's `AdminNav.tsx`
- `manage-page-template/*` — extracted from `pages/admin/ManageMarketingServices.tsx`
- `supabase/000_profiles_and_admin.sql` — distilled from `app/auth-migration-copy-paste.sql`
- `supabase/_content_table_template.sql` — synthesized from RLS patterns in `app/FIX_RLS_MANUALLY.sql`
