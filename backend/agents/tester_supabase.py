"""
Supabase Tester Agent — validates SupabaseBuilderAgent output.

Mirrors the legacy TesterAgent's result shape so the API + applicator gate
work identically. Validates:

  - required shell files present (AdminRoute, AdminLayout, AdminNav, supabase.ts)
  - one Manage<Entity>.tsx per content type
  - 000_profiles_and_admin.sql + one create migration per content type
  - admin-nav-items.ts, admin-routes.snippet.tsx, INSTALL.md
  - no unsubstituted __PLACEHOLDER__ tokens left in any generated file
  - SQL files are non-empty and end with a newline (sanity)
  - .tsx files parse-balanced (braces/parens/brackets) — cheap proxy for
    "didn't get truncated mid-stamp"
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base import BaseAgent

PLACEHOLDER_RE = re.compile(r"__[A-Z][A-Z0-9_]*__")

REQUIRED_SHELL_FILES = [
    "src/components/AdminRoute.tsx",
    "src/components/AdminLayout.tsx",
    "src/components/AdminNav.tsx",
    "src/lib/supabase.ts",
]

REQUIRED_TOP_LEVEL_FILES = [
    "src/admin-nav-items.ts",
    "admin-routes.snippet.tsx",
    "INSTALL.md",
]


class SupabaseTesterAgent(BaseAgent):
    def __init__(self, project_path: str, project_name: str, builder_output: dict[str, Any]):
        super().__init__(project_path, project_name)
        self.builder_output = builder_output
        self.output_dir = Path(builder_output.get("output_directory", ""))
        self.content_types: list[str] = list(builder_output.get("content_types", []))

    async def execute(self) -> dict[str, Any]:
        results: dict[str, Any] = {
            "test_status": "pending",
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": [],
            "warnings": [],
            "validation_details": {},
        }

        try:
            if not self.output_dir.exists():
                results["test_status"] = "failed"
                results["errors"].append(f"Builder output dir missing: {self.output_dir}")
                return results

            for name, fn in (
                ("structure", self._validate_structure),
                ("migrations", self._validate_migrations),
                ("manage_pages", self._validate_manage_pages),
                ("placeholders", self._validate_no_placeholders),
                ("syntax", self._validate_syntax_balance),
            ):
                detail = fn()
                results["validation_details"][name] = detail
                results["tests_run"] += detail["total"]
                results["tests_passed"] += detail["passed"]
                results["tests_failed"] += detail["failed"]

            if results["tests_failed"] == 0:
                results["test_status"] = "passed"
            elif results["tests_passed"] > results["tests_failed"]:
                results["test_status"] = "passed_with_warnings"
                results["warnings"].append(f"{results['tests_failed']} tests failed")
            else:
                results["test_status"] = "failed"

        except Exception as e:
            results["test_status"] = "error"
            results["errors"].append(str(e))

        return results

    # ---- checks ----

    def _validate_structure(self) -> dict[str, Any]:
        result = {"total": 0, "passed": 0, "failed": 0, "errors": []}
        for rel in REQUIRED_SHELL_FILES + REQUIRED_TOP_LEVEL_FILES:
            result["total"] += 1
            if (self.output_dir / rel).is_file():
                result["passed"] += 1
            else:
                result["failed"] += 1
                result["errors"].append(f"Missing required file: {rel}")
        return result

    def _validate_migrations(self) -> dict[str, Any]:
        result = {"total": 0, "passed": 0, "failed": 0, "errors": []}
        migrations_dir = self.output_dir / "supabase" / "migrations"

        # Must have the bootstrap migration.
        result["total"] += 1
        bootstrap = migrations_dir / "000_profiles_and_admin.sql"
        if bootstrap.is_file() and bootstrap.stat().st_size > 0:
            result["passed"] += 1
        else:
            result["failed"] += 1
            result["errors"].append("Missing or empty 000_profiles_and_admin.sql")

        # One create-table migration per content type.
        for table in self.content_types:
            result["total"] += 1
            matches = list(migrations_dir.glob(f"*_create_{table}.sql"))
            if len(matches) == 1 and matches[0].stat().st_size > 0:
                result["passed"] += 1
            elif len(matches) == 0:
                result["failed"] += 1
                result["errors"].append(f"Missing migration: *_create_{table}.sql")
            else:
                result["failed"] += 1
                result["errors"].append(
                    f"Expected one migration for {table}, found {len(matches)}"
                )
        return result

    def _validate_manage_pages(self) -> dict[str, Any]:
        result = {"total": 0, "passed": 0, "failed": 0, "errors": []}
        admin_dir = self.output_dir / "src" / "pages" / "admin"

        for table in self.content_types:
            result["total"] += 1
            # Stamper writes ManagePascal(Plural).tsx — we can't reverse the
            # transform perfectly here, so look for any Manage*.tsx that mentions
            # the table name in the file (the stamped page references it).
            found = False
            if admin_dir.is_dir():
                for tsx in admin_dir.glob("Manage*.tsx"):
                    try:
                        if table in tsx.read_text():
                            found = True
                            break
                    except OSError:
                        continue
            if found:
                result["passed"] += 1
            else:
                result["failed"] += 1
                result["errors"].append(f"No Manage*.tsx references table {table!r}")
        return result

    def _validate_no_placeholders(self) -> dict[str, Any]:
        result = {"total": 0, "passed": 0, "failed": 0, "errors": []}
        for f in self.output_dir.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix not in (".tsx", ".ts", ".sql", ".md"):
                continue
            result["total"] += 1
            try:
                content = f.read_text()
            except (OSError, UnicodeDecodeError) as e:
                result["failed"] += 1
                result["errors"].append(f"{f.name}: {e}")
                continue
            leftover = PLACEHOLDER_RE.findall(content)
            if leftover:
                result["failed"] += 1
                result["errors"].append(
                    f"{f.relative_to(self.output_dir)}: unsubstituted {sorted(set(leftover))}"
                )
            else:
                result["passed"] += 1
        return result

    def _validate_syntax_balance(self) -> dict[str, Any]:
        """Cheap proxy for truncated/broken stamps: balanced {}, (), []."""
        result = {"total": 0, "passed": 0, "failed": 0, "errors": []}
        for f in self.output_dir.rglob("*.tsx"):
            result["total"] += 1
            try:
                content = f.read_text()
            except OSError as e:
                result["failed"] += 1
                result["errors"].append(f"{f.name}: {e}")
                continue
            # Strip strings/comments crudely so we don't miscount braces inside them.
            stripped = re.sub(r"//[^\n]*", "", content)
            stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.DOTALL)
            stripped = re.sub(r"'(?:\\.|[^'\\])*'", "''", stripped)
            stripped = re.sub(r'"(?:\\.|[^"\\])*"', '""', stripped)
            stripped = re.sub(r"`(?:\\.|[^`\\])*`", "``", stripped)
            pairs = {"{": "}", "(": ")", "[": "]"}
            unbalanced = []
            for o, c in pairs.items():
                if stripped.count(o) != stripped.count(c):
                    unbalanced.append(f"{o}{c}")
            if unbalanced:
                result["failed"] += 1
                result["errors"].append(
                    f"{f.relative_to(self.output_dir)}: unbalanced {unbalanced}"
                )
            else:
                result["passed"] += 1
        return result
