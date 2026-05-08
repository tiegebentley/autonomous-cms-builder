"""
Unit tests for SupabaseBuilderAgent against the SPEC §8 fixture.

Verifies:
  - Spec normalization produces the right ContentTypeSpec list
  - 3 SQL migrations + 3 Manage*.tsx files emitted
  - Nav items reference the right icons (Target, MapPin, Users)
  - Generated files contain the expected substitutions
  - INSTALL.md is generated and lists every output

Run with: pytest backend/tests/test_builder_supabase.py -v
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

# Ensure backend/ is on sys.path so `agents.*` imports resolve when pytest is
# invoked from the repo root.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agents.builder_supabase import (  # noqa: E402
    SupabaseBuilderAgent,
    normalize_analyzer_output,
    _singular,
    _plural,
    _pascal,
)


# SPEC §8 fixture
FIXTURE_RECOMMENDATIONS = {
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


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def test_singular():
    assert _singular("services") == "service"
    assert _singular("locations") == "location"
    assert _singular("coaches") == "coach"
    assert _singular("faqs") == "faq"
    assert _singular("categories") == "category"


def test_plural():
    assert _plural("service") == "services"
    assert _plural("location") == "locations"
    assert _plural("coach") == "coaches"
    assert _plural("category") == "categories"


def test_pascal():
    assert _pascal("services") == "Services"
    assert _pascal("display_order") == "DisplayOrder"
    assert _pascal("image-url") == "ImageUrl"


# ---------------------------------------------------------------------------
# Spec normalization
# ---------------------------------------------------------------------------

def test_normalize_produces_three_specs():
    specs = normalize_analyzer_output(FIXTURE_RECOMMENDATIONS)
    assert len(specs) == 3
    assert {s["table_name"] for s in specs} == {"services", "locations", "coaches"}
    assert {s["entity"] for s in specs} == {"Service", "Location", "Coach"}


def test_normalize_assigns_correct_icons():
    specs = normalize_analyzer_output(FIXTURE_RECOMMENDATIONS)
    icon_by_table = {s["table_name"]: s["icon"] for s in specs}
    assert icon_by_table["services"] == "Target"
    assert icon_by_table["locations"] == "MapPin"
    assert icon_by_table["coaches"] == "Users"


def test_normalize_promotes_slug_field_type():
    specs = normalize_analyzer_output(FIXTURE_RECOMMENDATIONS)
    services = next(s for s in specs if s["table_name"] == "services")
    slug_field = next(f for f in services["fields"] if f["name"] == "slug")
    assert slug_field["type"] == "slug"


def test_normalize_detects_image_url_from_field_name():
    specs = normalize_analyzer_output(FIXTURE_RECOMMENDATIONS)
    locations = next(s for s in specs if s["table_name"] == "locations")
    image_field = next(f for f in locations["fields"] if f["name"] == "image_url")
    assert image_field["type"] == "image_url"

    coaches = next(s for s in specs if s["table_name"] == "coaches")
    photo_field = next(f for f in coaches["fields"] if f["name"] == "photo_url")
    assert photo_field["type"] == "image_url"


def test_normalize_promotes_array_to_string_array():
    specs = normalize_analyzer_output(FIXTURE_RECOMMENDATIONS)
    services = next(s for s in specs if s["table_name"] == "services")
    benefits = next(f for f in services["fields"] if f["name"] == "benefits")
    assert benefits["type"] == "string_array"


def test_normalize_uses_display_order_as_order_by():
    specs = normalize_analyzer_output(FIXTURE_RECOMMENDATIONS)
    for s in specs:
        assert s["order_by"] == "display_order"


def test_normalize_show_in_list_caps_at_three_non_array_fields():
    specs = normalize_analyzer_output(FIXTURE_RECOMMENDATIONS)
    services = next(s for s in specs if s["table_name"] == "services")
    shown = [f for f in services["fields"] if f["show_in_list"]]
    # benefits (array) and description (longtext) should be excluded.
    assert all(f["type"] not in ("string_array", "longtext", "image_url") for f in shown)
    assert len(shown) <= 3


# ---------------------------------------------------------------------------
# End-to-end build
# ---------------------------------------------------------------------------

@pytest.fixture
def built(tmp_path):
    """Run the full build into tmp_path, return (agent, result, output_dir)."""
    agent = SupabaseBuilderAgent(
        project_path=str(tmp_path),
        project_name="test-cms",
        analyzer_output={"cms_recommendations": FIXTURE_RECOMMENDATIONS},
    )
    result = asyncio.run(agent.execute())
    return agent, result, agent.output_dir


def test_build_completes(built):
    _, result, _ = built
    assert result["build_status"] == "completed", result.get("errors")
    assert result["files_generated"] > 0


def test_build_emits_three_migrations(built):
    _, _, out = built
    migrations = sorted((out / "supabase" / "migrations").glob("*.sql"))
    names = [m.name for m in migrations]
    assert "000_profiles_and_admin.sql" in names
    assert "001_create_services.sql" in names
    assert "002_create_locations.sql" in names
    assert "003_create_coaches.sql" in names


def test_build_emits_three_manage_pages(built):
    _, _, out = built
    pages = sorted((out / "src" / "pages" / "admin").glob("Manage*.tsx"))
    names = [p.name for p in pages]
    assert names == ["ManageCoaches.tsx", "ManageLocations.tsx", "ManageServices.tsx"]


def test_build_emits_shell_files(built):
    _, _, out = built
    components = out / "src" / "components"
    assert (components / "AdminRoute.tsx").exists()
    assert (components / "AdminNav.tsx").exists()
    assert (components / "AdminLayout.tsx").exists()
    assert (out / "src" / "lib" / "supabase.ts").exists()


def test_nav_items_file_references_correct_icons(built):
    _, _, out = built
    nav = (out / "src" / "admin-nav-items.ts").read_text()
    assert "Target" in nav
    assert "MapPin" in nav
    assert "Users" in nav
    # Path should be /admin/<table_name>
    assert "/admin/services" in nav
    assert "/admin/locations" in nav
    assert "/admin/coaches" in nav


def test_route_snippet_imports_all_pages(built):
    _, _, out = built
    snippet = (out / "admin-routes.snippet.tsx").read_text()
    assert "ManageServices" in snippet
    assert "ManageLocations" in snippet
    assert "ManageCoaches" in snippet
    assert "AdminLayout" in snippet


def test_install_md_lists_generated_files(built):
    _, result, out = built
    install = (out / "INSTALL.md").read_text()
    assert "supabase/migrations/000_profiles_and_admin.sql" in install
    assert "src/components/AdminRoute.tsx" in install
    # Spot-check it mentions the smoke-test path for the first content type.
    assert "/admin/" in install


def test_services_migration_has_slug_unique(built):
    _, _, out = built
    sql = (out / "supabase" / "migrations" / "001_create_services.sql").read_text()
    assert "slug text NOT NULL UNIQUE" in sql
    # benefits is a string_array → text[]
    assert "benefits text[]" in sql
    # RLS enabled
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "services_select_public" in sql
    assert "services_insert_admin" in sql


def test_services_manage_page_substitutions(built):
    _, _, out = built
    page = (out / "src" / "pages" / "admin" / "ManageServices.tsx").read_text()
    # No raw placeholders left.
    assert "{{" not in page, "Unsubstituted placeholders found"
    # Component name + table name + entity.
    assert "export default function ManageServices()" in page
    assert "from('services')" in page
    assert "Add Service" in page  # button label uses singular entity
    # Icon imported.
    assert "Target" in page
    # Array union for benefits.
    assert "'benefits'" in page
    # Form has slug input and benefits array UI.
    assert "updateField('slug'" in page
    assert "updateArrayField('benefits'" in page


def test_coaches_manage_page_no_array_union(built):
    """Coaches has no string_array fields → union should be `never`."""
    _, _, out = built
    page = (out / "src" / "pages" / "admin" / "ManageCoaches.tsx").read_text()
    assert "field: never" in page or "(field: never," in page


def test_stamped_pages_have_no_template_doc_block(built):
    """The template's authoring comments must not survive stamping."""
    _, _, out = built
    for page in (out / "src" / "pages" / "admin").glob("Manage*.tsx"):
        text = page.read_text()
        # First non-blank line should be a real import.
        first = next(line for line in text.splitlines() if line.strip())
        assert first.startswith("import "), (
            f"{page.name} starts with `{first[:80]}` — template doc-block leaked through"
        )


def test_no_unsubstituted_placeholders_anywhere(built):
    """Belt-and-suspenders: scan every generated file for `{{...}}` leftovers."""
    _, _, out = built
    leftovers = []
    for path in out.rglob("*"):
        if path.is_dir():
            continue
        if path.suffix in (".md",):
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        if "{{" in text and "}}" in text:
            # Allow only the verbatim base migration's docstring example, which
            # uses {{ in a SQL comment — but that file has no placeholders.
            leftovers.append(str(path.relative_to(out)))
    assert not leftovers, f"Unsubstituted placeholders in: {leftovers}"
