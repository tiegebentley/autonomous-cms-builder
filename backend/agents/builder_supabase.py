"""
Supabase Builder Agent — replaces the Kirby BuilderAgent.

Stamps `templates/admin-cms/` into a client repo:
  - Supabase migrations (000_profiles_and_admin + one per content type)
  - React admin pages (Manage<Entity> per content type)
  - Verbatim shell files (AdminRoute / AdminLayout / AdminNav / supabase.ts)
  - Generated nav-items + App.tsx route snippet + INSTALL.md

Design contract: see ../templates/admin-cms/SPEC.md
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any

from .base import BaseAgent


# ---------------------------------------------------------------------------
# Constants from SPEC §5 — ../templates/admin-cms/SPEC.md
# ---------------------------------------------------------------------------

ICONS: dict[str, str] = {
    "service": "Target", "services": "Target",
    "program": "Target", "programs": "Target",
    "location": "MapPin", "locations": "MapPin",
    "neighborhood": "MapPin", "neighborhoods": "MapPin",
    "coach": "Users", "coaches": "Users",
    "team": "Users", "teams": "Users",
    "player": "User", "players": "User",
    "testimonial": "MessageSquareQuote", "testimonials": "MessageSquareQuote",
    "review": "Star", "reviews": "Star",
    "event": "Calendar", "events": "Calendar",
    "session": "Calendar", "sessions": "Calendar",
    "package": "Package", "packages": "Package",
    "faq": "HelpCircle", "faqs": "HelpCircle",
    "blog": "FileText", "post": "FileText", "posts": "FileText",
    "page": "FileText", "pages": "FileText",
    "hero": "Sparkles",
    "settings": "Settings",
}

# SPEC §1 — analyzer field type → spec type
ANALYZER_TYPE_MAP: dict[str, str] = {
    "text": "text",
    "string": "text",
    "textarea": "longtext",
    "longtext": "longtext",
    "number": "number",
    "int": "number",
    "integer": "number",
    "boolean": "boolean",
    "bool": "boolean",
    "array": "string_array",
    "list": "string_array",
    "string_array": "string_array",
    "image": "image_url",
    "image_url": "image_url",
    "url": "text",
    "slug": "slug",
    "date": "date",
    "datetime": "date",
    "files": "image_url",  # analyzer's "files" output is almost always an image
}

# SPEC §2 — spec type → Postgres column
SQL_TYPE_MAP: dict[str, str] = {
    "text": "text",
    "longtext": "text",
    "number": "integer",
    "boolean": "boolean NOT NULL DEFAULT false",
    "string_array": "text[] NOT NULL DEFAULT '{}'",
    "image_url": "text",
    "slug": "text NOT NULL UNIQUE",
    "date": "date",
}

# SPEC §3 — spec type → TypeScript type
TS_TYPE_MAP: dict[str, str] = {
    "text": "string",
    "longtext": "string",
    "number": "number",
    "boolean": "boolean",
    "string_array": "string[]",
    "image_url": "string",
    "slug": "string",
    "date": "string",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _singular(word: str) -> str:
    """Crude English singularizer — good enough for content-type keys.

    Handles the cases we actually see: services→service, coaches→coach,
    locations→location, faqs→faq. Falls back to identity.
    """
    w = word.lower()
    if w.endswith("ies") and len(w) > 3:
        return w[:-3] + "y"
    if w.endswith("ches") or w.endswith("shes") or w.endswith("xes"):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _plural(word: str) -> str:
    """Inverse of _singular for the nav label / button text."""
    w = word.lower()
    if w.endswith("y") and len(w) > 1 and w[-2] not in "aeiou":
        return w[:-1] + "ies"
    if w.endswith(("ch", "sh", "x", "s")):
        return w + "es"
    if w.endswith("s"):
        return w
    return w + "s"


def _pascal(word: str) -> str:
    """snake_or_kebab → PascalCase."""
    return "".join(p.capitalize() for p in re.split(r"[_\-\s]+", word) if p)


def _title(word: str) -> str:
    """field_name → Field Name."""
    return " ".join(p.capitalize() for p in re.split(r"[_\-\s]+", word) if p)


def _icon_for(key: str) -> str:
    return ICONS.get(key.lower(), "LayoutGrid")


# ---------------------------------------------------------------------------
# Spec normalization (SPEC §1 adapter)
# ---------------------------------------------------------------------------

def normalize_analyzer_output(
    recommendations: dict[str, Any],
) -> list[dict[str, Any]]:
    """Convert analyzer's `cms_recommendations` dict into a list of ContentTypeSpec.

    Input:  { "services": { "fields": [{name,type,required}, ...] }, ... }
    Output: [ { entity, table_name, icon, order_by, fields: [...] }, ... ]
    """
    specs: list[dict[str, Any]] = []
    for key, cfg in recommendations.items():
        table_name = key.lower().replace("-", "_")
        entity = _pascal(_singular(table_name))

        raw_fields = cfg.get("fields", []) or []
        fields = [_normalize_field(f) for f in raw_fields if isinstance(f, dict)]

        # SPEC §1 — auto-add display_order if missing
        if not any(f["name"] == "display_order" for f in fields):
            fields.append({
                "name": "display_order",
                "label": "Display Order",
                "type": "number",
                "required": False,
                "placeholder": None,
                "show_in_list": False,
            })

        order_by = "display_order" if any(
            f["name"] == "display_order" for f in fields
        ) else "created_at"

        # show_in_list defaults: first 3 non-id, non-array fields
        _set_show_in_list(fields)

        specs.append({
            "entity": entity,
            "table_name": table_name,
            "icon": _icon_for(table_name),
            "order_by": order_by,
            "fields": fields,
        })
    return specs


def _normalize_field(raw: dict[str, Any]) -> dict[str, Any]:
    name = raw.get("name", "").strip()
    raw_type = (raw.get("type") or "text").lower()

    # SPEC §1 — special case: field name == "slug" forces slug type
    if name == "slug":
        spec_type = "slug"
    # SPEC §1 — name contains "image" or "photo" + url-ish type → image_url
    elif raw_type in ("url", "image", "image_url") or "image" in name or "photo" in name:
        spec_type = "image_url" if "image" in name or "photo" in name or raw_type in ("image", "image_url") else "text"
    else:
        spec_type = ANALYZER_TYPE_MAP.get(raw_type, "text")

    return {
        "name": name,
        "label": _title(name),
        "type": spec_type,
        "required": bool(raw.get("required", False)),
        "placeholder": raw.get("placeholder"),
        "show_in_list": True,  # overwritten by _set_show_in_list
    }


def _set_show_in_list(fields: list[dict[str, Any]]) -> None:
    """SPEC §6 — first 3 non-array, non-longtext, non-image_url fields show in list card."""
    shown = 0
    for f in fields:
        if f["type"] in ("string_array", "longtext", "image_url"):
            f["show_in_list"] = False
            continue
        if shown < 3:
            f["show_in_list"] = True
            shown += 1
        else:
            f["show_in_list"] = False


# ---------------------------------------------------------------------------
# Stampers
# ---------------------------------------------------------------------------

class TemplateStamper:
    """Reads the admin-cms template directory and stamps files into output_dir."""

    def __init__(self, template_root: Path, output_dir: Path):
        self.template_root = template_root
        self.output_dir = output_dir

    # ----- shell (verbatim copies) -----

    def stamp_shell(self) -> list[Path]:
        """Copy shell/ files verbatim into output_dir."""
        out_components = self.output_dir / "src" / "components"
        out_lib = self.output_dir / "src" / "lib"
        out_components.mkdir(parents=True, exist_ok=True)
        out_lib.mkdir(parents=True, exist_ok=True)

        written = []
        for fname in ("AdminRoute.tsx", "AdminNav.tsx", "AdminLayout.tsx"):
            dest = out_components / fname
            shutil.copyfile(self.template_root / "shell" / fname, dest)
            written.append(dest)

        dest = out_lib / "supabase.ts"
        shutil.copyfile(self.template_root / "shell" / "supabase.ts", dest)
        written.append(dest)
        return written

    # ----- supabase migrations -----

    def stamp_base_migration(self) -> Path:
        """Copy 000_profiles_and_admin.sql verbatim."""
        out_dir = self.output_dir / "supabase" / "migrations"
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / "000_profiles_and_admin.sql"
        shutil.copyfile(
            self.template_root / "supabase" / "000_profiles_and_admin.sql",
            dest,
        )
        # Also copy the manual-step helper.
        shutil.copyfile(
            self.template_root / "supabase" / "set-admin.sql",
            self.output_dir / "supabase" / "set-admin.sql",
        )
        return dest

    def stamp_content_migration(self, spec: dict[str, Any], index: int) -> Path:
        """Stamp _content_table_template.sql for one content type.

        index is 1-based; emits files like 001_create_services.sql.
        """
        tpl = (self.template_root / "supabase" / "_content_table_template.sql").read_text()

        columns = []
        for f in spec["fields"]:
            sql_type = SQL_TYPE_MAP[f["type"]]
            # NOT NULL is already in some defaults; only append if required and not present.
            if f["required"] and "NOT NULL" not in sql_type and f["type"] != "slug":
                sql_type += " NOT NULL"
            columns.append(f"  {f['name']} {sql_type}")
        columns_block = ",\n".join(columns)

        rendered = (
            tpl
            .replace("{{TABLE_NAME}}", spec["table_name"])
            .replace("{{COLUMNS_BLOCK}}", columns_block)
            .replace("{{ORDER_BY}}", spec["order_by"])
        )

        out_dir = self.output_dir / "supabase" / "migrations"
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"{index:03d}_create_{spec['table_name']}.sql"
        dest.write_text(rendered)
        return dest

    # ----- Manage<Entity>.tsx -----

    def stamp_manage_page(self, spec: dict[str, Any]) -> Path:
        """Stamp Manage<EntityPlural>.tsx for one content type."""
        tpl = (
            self.template_root
            / "manage-page-template"
            / "Manage__ENTITY_PASCAL__.tsx.tpl"
        ).read_text()

        entity = spec["entity"]                          # e.g. "Service"
        # table_name is already plural; PascalCase it directly.
        plural = _pascal(spec["table_name"])             # e.g. "Services"

        interface_fields = "\n  ".join(
            f"{f['name']}: {TS_TYPE_MAP[f['type']]};"
            for f in spec["fields"]
        )
        empty_fields = "\n    ".join(
            f"{f['name']}: {_empty_value_for(f)},"
            for f in spec["fields"]
        )

        array_field_names = [f["name"] for f in spec["fields"] if f["type"] == "string_array"]
        if array_field_names:
            array_union = " | ".join(f"'{n}'" for n in array_field_names)
        else:
            array_union = "never"

        list_card_body = _build_list_card_body(spec)
        form_body = _build_form_body(spec)

        rendered = (
            tpl
            .replace("{{ENTITY_PASCAL}}", entity)
            .replace("{{ENTITY_PLURAL}}", plural)
            .replace("{{ENTITY_LOWER}}", entity.lower())
            .replace("{{TABLE_NAME}}", spec["table_name"])
            .replace("{{ORDER_BY}}", spec["order_by"])
            .replace("{{INTERFACE_FIELDS}}", interface_fields)
            .replace("{{EMPTY_FIELDS}}", empty_fields)
            .replace("{{ARRAY_FIELDS_UNION}}", array_union)
            .replace("{{LIST_CARD_BODY}}", list_card_body)
            .replace("{{FORM_BODY}}", form_body)
            .replace("{{ICON_NAME}}", spec["icon"])
        )

        out_dir = self.output_dir / "src" / "pages" / "admin"
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"Manage{plural}.tsx"
        dest.write_text(rendered)
        return dest

    # ----- nav items + route snippet + install -----

    def stamp_nav_items(self, specs: list[dict[str, Any]]) -> Path:
        """Generate src/admin-nav-items.ts."""
        icon_imports = sorted({s["icon"] for s in specs} | {"Settings"})
        items_lines = []
        for s in specs:
            plural = _pascal(s["table_name"])
            items_lines.append(
                f"  {{ path: '/admin/{s['table_name']}', "
                f"label: '{plural}', Icon: {s['icon']} }},"
            )

        body = (
            f"import {{ {', '.join(icon_imports)} }} from 'lucide-react';\n"
            "import type { AdminNavItem } from './components/AdminNav';\n\n"
            "export const ADMIN_NAV_ITEMS: AdminNavItem[] = [\n"
            + "\n".join(items_lines)
            + "\n];\n"
        )
        dest = self.output_dir / "src" / "admin-nav-items.ts"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(body)
        return dest

    def stamp_route_snippet(self, specs: list[dict[str, Any]]) -> Path:
        """Generate the JSX snippet to paste into client App.tsx."""
        imports = []
        routes = []
        for s in specs:
            plural = _pascal(s["table_name"])
            imports.append(
                f"import Manage{plural} from './pages/admin/Manage{plural}';"
            )
            routes.append(
                f'        <Route path="{s["table_name"]}" element={{<Manage{plural} />}} />'
            )

        snippet = (
            "// Paste these imports near the top of App.tsx:\n"
            "import { AdminLayout } from './components/AdminLayout';\n"
            "import { ADMIN_NAV_ITEMS } from './admin-nav-items';\n"
            + "\n".join(imports)
            + "\n\n// Paste this <Route> inside your top-level <Routes>:\n"
            "<Route path=\"/admin/*\" element={\n"
            "  <AdminLayout navItems={ADMIN_NAV_ITEMS}>\n"
            "    <Routes>\n"
            + "\n".join(routes)
            + "\n    </Routes>\n"
            "  </AdminLayout>\n"
            "} />\n"
        )
        dest = self.output_dir / "admin-routes.snippet.tsx"
        dest.write_text(snippet)
        return dest

    def stamp_install_md(self, specs: list[dict[str, Any]], generated: list[Path]) -> Path:
        """Generate INSTALL.md listing every step the user needs to take."""
        rel = lambda p: str(p.relative_to(self.output_dir))
        files_block = "\n".join(f"- `{rel(p)}`" for p in generated)

        body = f"""# Install — admin CMS

Generated by autonomous-cms-builder. {len(specs)} content type(s) detected.

## Files generated

{files_block}

## Steps

1. **Apply Supabase migrations.** In your Supabase project SQL editor, run each
   migration file in `supabase/migrations/` in order. Start with `000_profiles_and_admin.sql`.

2. **Promote the first admin.** After signing up via the app once, edit
   `supabase/set-admin.sql` (replace the email) and run it in the SQL editor.

3. **Set frontend env vars.** In the client repo's `.env.local`:
   ```
   VITE_SUPABASE_URL=https://<your-project>.supabase.co
   VITE_SUPABASE_ANON_KEY=<your-anon-key>
   ```

4. **Copy generated `src/` files into the client repo.** Files in this output
   directory under `src/` are drop-in: copy them to the client repo's `src/`
   tree at the same paths.

5. **Wire up the admin route.** Open `admin-routes.snippet.tsx` and paste the
   imports + `<Route>` block into the client repo's `App.tsx`.

6. **Verify dependencies.** The client repo needs:
   `react-router-dom`, `@supabase/supabase-js`, `lucide-react`, and shadcn/ui
   primitives at `@/components/ui/{{button,input,textarea,dialog}}` plus
   `@/hooks/use-toast`. If any are missing, install them.

7. **Smoke-test.** `npm run dev`, sign up, run the SQL from step 2, then visit
   `/admin/{specs[0]['table_name']}` if everything wired correctly.
"""
        dest = self.output_dir / "INSTALL.md"
        dest.write_text(body)
        return dest


# ---------------------------------------------------------------------------
# Field-level renderers (SPEC §4 + §6)
# ---------------------------------------------------------------------------

def _empty_value_for(field: dict[str, Any]) -> str:
    """JS literal for the field's default in the `empty` object."""
    return {
        "text": "''",
        "longtext": "''",
        "slug": "''",
        "image_url": "''",
        "number": "0",
        "boolean": "false",
        "string_array": "['']",
        "date": "''",
    }[field["type"]]


def _build_list_card_body(spec: dict[str, Any]) -> str:
    """SPEC §6 — title (with icon) + slug inline + up to 2 secondary fields."""
    fields = spec["fields"]
    icon = spec["icon"]

    shown = [f for f in fields if f.get("show_in_list")]
    if not shown:
        return f'<h3 className="text-xl font-bold">{{item.id}}</h3>'

    title = shown[0]
    slug_field = next((f for f in fields if f["type"] == "slug"), None)
    secondary = [f for f in shown[1:3]]

    parts = []
    title_jsx = (
        '<div className="flex items-center gap-2 mb-2">\n'
        f'                  <{icon} className="h-5 w-5 text-blue-600" />\n'
        f'                  <h3 className="text-xl font-bold">{{item.{title["name"]}}}</h3>\n'
    )
    if slug_field and slug_field["name"] != title["name"]:
        title_jsx += (
            f'                  <span className="text-sm text-gray-500">/{{item.{slug_field["name"]}}}</span>\n'
        )
    title_jsx += "                </div>"
    parts.append(title_jsx)

    for i, f in enumerate(secondary):
        cls = "text-gray-600 mb-2" if i == 0 else "text-sm text-gray-700"
        parts.append(f'<p className="{cls}">{{item.{f["name"]}}}</p>')

    return "\n                ".join(parts)


def _build_form_body(spec: dict[str, Any]) -> str:
    """SPEC §4 — concatenate per-field-type form fragments."""
    parts = [_form_fragment(f) for f in spec["fields"]]
    return "\n              ".join(parts)


def _form_fragment(f: dict[str, Any]) -> str:
    """Render one form field. Mirrors _form-fragments.md but inlined for simplicity."""
    name, label, ftype = f["name"], f["label"], f["type"]
    placeholder = f.get("placeholder") or ""

    if ftype == "date":
        return (
            "<div>\n"
            f'                <label className="block text-sm font-medium mb-1">{label}</label>\n'
            "                <Input\n"
            "                  type=\"date\"\n"
            f"                  value={{editing.{name}}}\n"
            f"                  onChange={{(e) => updateField('{name}', e.target.value)}}\n"
            "                />\n"
            "              </div>"
        )

    if ftype in ("text", "slug", "image_url"):
        # image_url gets a preview underneath
        preview = (
            "\n                {editing." + name + " && (\n"
            "                  <img src={editing." + name + '} alt="" className="mt-2 max-h-32 rounded border" />\n'
            "                )}"
            if ftype == "image_url" else ""
        )
        return (
            "<div>\n"
            f'                <label className="block text-sm font-medium mb-1">{label}</label>\n'
            "                <Input\n"
            f"                  value={{editing.{name}}}\n"
            f"                  onChange={{(e) => updateField('{name}', e.target.value)}}\n"
            f'                  placeholder="{placeholder}"\n'
            "                />"
            f"{preview}\n"
            "              </div>"
        )

    if ftype == "longtext":
        return (
            "<div>\n"
            f'                <label className="block text-sm font-medium mb-1">{label}</label>\n'
            "                <Textarea\n"
            f"                  value={{editing.{name}}}\n"
            f"                  onChange={{(e) => updateField('{name}', e.target.value)}}\n"
            f'                  placeholder="{placeholder}"\n'
            "                  rows={3}\n"
            "                />\n"
            "              </div>"
        )

    if ftype == "number":
        return (
            "<div>\n"
            f'                <label className="block text-sm font-medium mb-1">{label}</label>\n'
            "                <Input\n"
            "                  type=\"number\"\n"
            f"                  value={{editing.{name}}}\n"
            f"                  onChange={{(e) => updateField('{name}', parseInt(e.target.value))}}\n"
            "                />\n"
            "              </div>"
        )

    if ftype == "boolean":
        return (
            '<div className="flex items-center gap-2">\n'
            "                <input\n"
            "                  type=\"checkbox\"\n"
            f'                  id="{name}"\n'
            f"                  checked={{editing.{name}}}\n"
            f"                  onChange={{(e) => updateField('{name}', e.target.checked)}}\n"
            "                />\n"
            f'                <label htmlFor="{name}" className="text-sm font-medium">{label}</label>\n'
            "              </div>"
        )

    if ftype == "string_array":
        return (
            "<div>\n"
            f'                <label className="block text-sm font-medium mb-1">{label}</label>\n'
            f"                {{editing.{name}.map((item, index) => (\n"
            "                  <div key={index} className=\"flex gap-2 mb-2\">\n"
            "                    <Input\n"
            "                      value={item}\n"
            f"                      onChange={{(e) => updateArrayField('{name}', index, e.target.value)}}\n"
            f'                      placeholder="{placeholder}"\n'
            "                    />\n"
            "                    <Button\n"
            "                      type=\"button\"\n"
            "                      variant=\"outline\"\n"
            "                      size=\"sm\"\n"
            f"                      onClick={{() => removeArrayItem('{name}', index)}}\n"
            "                    >\n"
            "                      <X className=\"h-4 w-4\" />\n"
            "                    </Button>\n"
            "                  </div>\n"
            "                ))}\n"
            "                <Button\n"
            "                  type=\"button\"\n"
            "                  variant=\"outline\"\n"
            "                  size=\"sm\"\n"
            f"                  onClick={{() => addArrayItem('{name}')}}\n"
            "                >\n"
            "                  <Plus className=\"mr-2 h-4 w-4\" />\n"
            f"                  Add {label}\n"
            "                </Button>\n"
            "              </div>"
        )

    # Fallback — shouldn't reach here.
    return f"<!-- Unknown field type: {ftype} for {name} -->"


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class SupabaseBuilderAgent(BaseAgent):
    """Stamps the admin-cms template into <project_path>/cms-generated/."""

    TEMPLATE_ROOT = (
        Path(__file__).resolve().parents[2] / "templates" / "admin-cms"
    )

    def __init__(
        self,
        project_path: str,
        project_name: str,
        analyzer_output: dict[str, Any],
        critic_output: dict[str, Any] | None = None,
    ):
        super().__init__(project_path, project_name)
        self.analyzer_output = analyzer_output
        self.critic_output = critic_output or {}
        self.output_dir = Path(project_path) / "cms-generated"

    async def execute(self) -> dict[str, Any]:
        recommendations = self.analyzer_output.get("cms_recommendations", {})
        if not recommendations:
            return {
                "build_status": "failed",
                "errors": ["No content types in analyzer output (cms_recommendations empty)"],
                "files_generated": 0,
            }

        specs = normalize_analyzer_output(recommendations)

        # Wipe + recreate output dir for a clean stamp.
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True)

        stamper = TemplateStamper(self.TEMPLATE_ROOT, self.output_dir)
        generated: list[Path] = []

        # 1. Verbatim shell + base migration.
        generated.extend(stamper.stamp_shell())
        generated.append(stamper.stamp_base_migration())

        # 2. Per-content-type files.
        for i, spec in enumerate(specs, start=1):
            generated.append(stamper.stamp_content_migration(spec, i))
            generated.append(stamper.stamp_manage_page(spec))

        # 3. Nav-items + route snippet + install doc.
        generated.append(stamper.stamp_nav_items(specs))
        generated.append(stamper.stamp_route_snippet(specs))
        generated.append(stamper.stamp_install_md(specs, generated.copy()))

        return {
            "build_status": "completed",
            "files_generated": len(generated),
            "content_types": [s["table_name"] for s in specs],
            "output_directory": str(self.output_dir),
            "files": [str(p.relative_to(self.output_dir)) for p in generated],
        }
