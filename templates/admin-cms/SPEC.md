# admin-cms Builder Spec

Pins the contract between the analyzer and the Supabase builder so the substitution
algorithm is deterministic and testable.

Status: design-locked 2026-05-08. Code lives in `backend/agents/builder_supabase.py`
(to be written next).

## 1. Builder input

The builder takes one object per content type the analyzer detected:

```python
ContentTypeSpec = {
    "entity": str,              # singular Title Case, e.g. "Service", "Coach"
    "table_name": str,          # snake_case plural, e.g. "services", "coaches"
    "icon": str,                # lucide-react icon name, e.g. "Target", "Users"
    "order_by": str,            # column name to sort the list view by
    "fields": [FieldSpec, ...]  # ordered; first non-id field becomes the card title
}

FieldSpec = {
    "name": str,                # snake_case column name
    "label": str,               # Title Case label for forms
    "type": Literal[
        "text", "longtext", "number", "boolean",
        "string_array", "image_url", "slug"
    ],
    "required": bool,           # NOT NULL on the SQL side; not enforced in form (yet)
    "placeholder": str | None,  # optional form hint
    "show_in_list": bool        # render in card body? default true for first 3 non-id fields
}
```

The analyzer's current output (`recommendations[type] = { fields: [{name,type,required}] }`)
is **not yet in this shape**. The builder accepts an analyzer output and runs an
adapter (`_normalize_analyzer_output`) to produce a list of `ContentTypeSpec`s.
Adapter rules:

- `entity` ← Title-cased singular of the recommendation key (`"services"` → `"Service"`).
  Use `inflect` lib or hand-roll: drop trailing `s`, strip suffix variants.
- `table_name` ← snake_case plural of the key.
- `icon` ← simple lookup table (see §5). Default `LayoutGrid` if no match.
- `order_by` ← `display_order` if present in fields, else `created_at`.
- For each analyzer field:
  - `text` (analyzer) → `text` (spec)
  - `textarea` → `longtext`
  - `number` / `int` → `number`
  - `boolean` / `bool` → `boolean`
  - `array` / `list` → `string_array`
  - `image` / `url` containing "image"/"photo" → `image_url`
  - field name == `slug` → `slug` (forces UNIQUE in SQL)
  - unknown → `text` (with a warning in the result)
- Auto-add `display_order: number` if not present (so cards have a stable order).

## 2. Type → SQL mapping

| Spec type      | Postgres column                                   |
|----------------|---------------------------------------------------|
| `text`         | `text`                                            |
| `longtext`     | `text`                                            |
| `number`       | `integer`                                         |
| `boolean`      | `boolean NOT NULL DEFAULT false`                  |
| `string_array` | `text[] NOT NULL DEFAULT '{}'`                    |
| `image_url`    | `text`                                            |
| `slug`         | `text NOT NULL UNIQUE`                            |

Required fields get `NOT NULL` appended (except where the default already covers it).

## 3. Type → TypeScript mapping (for `INTERFACE_FIELDS`)

| Spec type      | TS type                |
|----------------|------------------------|
| `text`         | `string`               |
| `longtext`     | `string`               |
| `number`       | `number`               |
| `boolean`      | `boolean`              |
| `string_array` | `string[]`             |
| `image_url`    | `string`               |
| `slug`         | `string`               |

## 4. Type → form fragment (for `FORM_BODY`)

Direct lookup into `manage-page-template/_form-fragments.md`:

| Spec type      | Fragment           |
|----------------|--------------------|
| `text`         | "Short text"       |
| `slug`         | "Short text"       |
| `image_url`    | "Image URL"        |
| `longtext`     | "Long text"        |
| `number`       | "Number"           |
| `boolean`      | "Boolean"          |
| `string_array` | "String array"     |

Per-fragment substitution: `__FIELD__` → `field.name`, `__LABEL__` → `field.label`,
`__PLACEHOLDER__` → `field.placeholder` (or empty string).

## 5. Icon lookup

Hand-curated map for common soccer-site entities. Anything not matched → `LayoutGrid`.

```python
ICONS = {
    "service": "Target", "services": "Target",
    "program": "Target", "programs": "Target",
    "location": "MapPin", "locations": "MapPin",
    "neighborhood": "MapPin",
    "coach": "Users", "coaches": "Users",
    "team": "Users",
    "player": "User",
    "testimonial": "MessageSquareQuote", "testimonials": "MessageSquareQuote",
    "review": "Star", "reviews": "Star",
    "event": "Calendar", "events": "Calendar",
    "session": "Calendar",
    "package": "Package", "packages": "Package",
    "faq": "HelpCircle", "faqs": "HelpCircle",
    "blog": "FileText", "post": "FileText", "posts": "FileText",
    "page": "FileText", "pages": "FileText",
    "hero": "Sparkles",
    "settings": "Settings",
}
```

## 6. List-card body rule

Goal: don't generate cluttered cards. Default body = first 3 fields where
`show_in_list = True`, rendered as:

- field 0 → `<h3 className="text-xl font-bold">{item.<name>}</h3>` (with `<Icon />` prefix)
- field 1 → `<p className="text-gray-600 mb-2">{item.<name>}</p>`
- field 2+ → `<p className="text-sm text-gray-700">{item.<name>}</p>`

Skip `string_array`, `longtext`, `image_url` for fields 1-2 (they don't render
nicely in a one-line summary). Render `slug` inline as `<span className="text-sm text-gray-500">/{item.slug}</span>` next to the title.

## 7. Builder outputs

For each `ContentTypeSpec`:

1. `output_dir/supabase/migrations/0NN_create_<table_name>.sql`
   — stamped from `supabase/_content_table_template.sql`
2. `output_dir/src/pages/admin/Manage<EntityPlural>.tsx`
   — stamped from `manage-page-template/Manage__ENTITY_PASCAL__.tsx.tpl`

Once per build (regardless of how many content types):

3. `output_dir/supabase/migrations/000_profiles_and_admin.sql` — verbatim copy
4. `output_dir/src/components/AdminRoute.tsx` — verbatim
5. `output_dir/src/components/AdminLayout.tsx` — verbatim
6. `output_dir/src/components/AdminNav.tsx` — verbatim (the `items` array is supplied at call site, not baked in)
7. `output_dir/src/lib/supabase.ts` — verbatim
8. `output_dir/src/admin-nav-items.ts` — generated, exports `ADMIN_NAV_ITEMS: AdminNavItem[]`
9. `output_dir/admin-routes.snippet.tsx` — generated, the JSX snippet to paste into `App.tsx`
10. `output_dir/INSTALL.md` — generated, lists exact steps to wire into client repo

`output_dir` is `<project_path>/cms-generated/` (sibling of the Higgsfield site source, so
the user can review before letting the applicator merge it in).

## 8. Test fixture

The first thing the builder gets unit-tested against is a hand-crafted analyzer
output for a 3-content-type soccer site:

```python
FIXTURE = {
    "services": {"fields": [
        {"name": "slug", "type": "text", "required": True},
        {"name": "name", "type": "text", "required": True},
        {"name": "tagline", "type": "text", "required": False},
        {"name": "description", "type": "textarea", "required": False},
        {"name": "benefits", "type": "array", "required": False},
        {"name": "pricing_display", "type": "text", "required": False},
        {"name": "display_order", "type": "number", "required": False},
    ]},
    "locations": {"fields": [
        {"name": "slug", "type": "text", "required": True},
        {"name": "name", "type": "text", "required": True},
        {"name": "address", "type": "text", "required": False},
        {"name": "image_url", "type": "image", "required": False},
        {"name": "description", "type": "textarea", "required": False},
        {"name": "display_order", "type": "number", "required": False},
    ]},
    "coaches": {"fields": [
        {"name": "name", "type": "text", "required": True},
        {"name": "title", "type": "text", "required": False},
        {"name": "bio", "type": "textarea", "required": False},
        {"name": "photo_url", "type": "image", "required": False},
        {"name": "display_order", "type": "number", "required": False},
    ]},
}
```

Pass criteria for the unit test:
- 3 SQL migration files emitted, each compiles in psql syntax check
- 3 `.tsx` files emitted, each passes `tsc --noEmit` against a stub project
- `ADMIN_NAV_ITEMS` array has 3 entries with correct icons (Target, MapPin, Users)
- `INSTALL.md` lists all 8 generated paths

## 9. What the builder does NOT do (yet)

Out of scope for the first cut — surface these as future work, don't half-ship them:

- Patching the client repo's `App.tsx` (manual paste from `admin-routes.snippet.tsx` for now)
- Rewriting the client's frontend pages to fetch from Supabase (separate agent: `integrator.py` already exists, gets repurposed later)
- Foreign-key relationships between content types (e.g. coach → location)
- Image upload UI (the `image_url` field is just a text input for now)
- Auth UI (signup/login pages) — assume the Higgsfield site or a separate template provides them
- Per-tenant Supabase provisioning — manual via dashboard
