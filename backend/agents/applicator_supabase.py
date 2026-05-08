"""
Supabase Applicator Agent — replaces the Kirby ApplicatorAgent.

Takes the SupabaseBuilderAgent's output (`<project>/cms-generated/`) and merges
it into the actual client repo:

  - copies `cms-generated/src/**` into `<project>/src/**` (with backup of any
    file we'd overwrite)
  - leaves `cms-generated/supabase/` untouched (user runs migrations manually
    in their Supabase SQL editor — see INSTALL.md)
  - leaves `admin-routes.snippet.tsx` and `INSTALL.md` in place for user to read

Honours `auto_apply=False` by stopping after backup + dry-run inventory.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import BaseAgent


class SupabaseApplicatorAgent(BaseAgent):
    BACKUP_ROOT_NAME = ".cms-backups"

    def __init__(
        self,
        project_path: str,
        project_name: str,
        builder_output: dict[str, Any],
        tester_output: dict[str, Any] | None = None,
        auto_apply: bool = False,
    ):
        super().__init__(project_path, project_name)
        self.builder_output = builder_output
        self.tester_output = tester_output or {}
        self.auto_apply = auto_apply

        self.source_dir = Path(builder_output.get("output_directory", ""))
        self.project_root = Path(project_path)
        self.backup_dir: Path | None = None

    async def execute(self) -> dict[str, Any]:
        results: dict[str, Any] = {
            "apply_status": "pending",
            "auto_apply": self.auto_apply,
            "backup_location": None,
            "files_to_apply": [],
            "files_applied": [],
            "files_skipped": [],
            "errors": [],
            "warnings": [],
            "next_steps": [],
        }

        # 1. Validate inputs.
        if not self.source_dir.exists():
            results["apply_status"] = "failed"
            results["errors"].append(
                f"Builder output directory not found: {self.source_dir}"
            )
            return results

        src_root = self.source_dir / "src"
        if not src_root.exists():
            results["apply_status"] = "failed"
            results["errors"].append(
                f"Builder didn't produce src/: {src_root} (was the SupabaseBuilderAgent run?)"
            )
            return results

        # If tests were run, gate on them. If absent, don't block.
        test_status = self.tester_output.get("test_status")
        if test_status and test_status not in ("passed", "passed_with_warnings"):
            results["apply_status"] = "skipped"
            results["errors"].append(f"Tests did not pass (status={test_status})")
            return results

        # 2. Plan: which files would we copy, and which would overwrite?
        plan = self._plan_copies(src_root)
        results["files_to_apply"] = [
            {"src": str(p["src"]), "dest": str(p["dest"]), "overwrites": p["overwrites"]}
            for p in plan
        ]

        # 3. If auto_apply is off, stop here as a dry-run.
        if not self.auto_apply:
            results["apply_status"] = "awaiting_approval"
            results["warnings"].append(
                "auto_apply=False — no files copied. Re-run with auto_apply=True to merge."
            )
            results["next_steps"] = self._build_next_steps()
            return results

        # 4. Backup any file that would be overwritten.
        backup_info = self._create_backup([p for p in plan if p["overwrites"]])
        results["backup_location"] = backup_info.get("location")

        # 5. Copy.
        for item in plan:
            try:
                item["dest"].parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(item["src"], item["dest"])
                results["files_applied"].append(str(item["dest"].relative_to(self.project_root)))
            except Exception as e:
                results["errors"].append(f"Failed to copy {item['src']}: {e}")

        # 6. Verify.
        all_present = all(item["dest"].exists() for item in plan)
        if not all_present:
            results["apply_status"] = "failed"
            results["errors"].append("One or more destination files missing after copy")
            return results

        if results["errors"]:
            results["apply_status"] = "completed_with_errors"
        else:
            results["apply_status"] = "completed"

        results["next_steps"] = self._build_next_steps()
        return results

    # ---- helpers ----

    def _plan_copies(self, src_root: Path) -> list[dict[str, Any]]:
        """Return list of {src, dest, overwrites} for every file under src_root."""
        plan = []
        target_src = self.project_root / "src"
        for src_file in src_root.rglob("*"):
            if not src_file.is_file():
                continue
            rel = src_file.relative_to(src_root)
            dest = target_src / rel
            plan.append({
                "src": src_file,
                "dest": dest,
                "overwrites": dest.exists(),
            })
        return plan

    def _create_backup(self, items_to_backup: list[dict[str, Any]]) -> dict[str, Any]:
        """Backup every file we're about to overwrite. Empty list → no backup made."""
        info: dict[str, Any] = {"location": None, "files": []}
        if not items_to_backup:
            return info

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_dir = self.project_root / self.BACKUP_ROOT_NAME / f"backup_{timestamp}"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "timestamp": timestamp,
            "project_name": self.project_name,
            "project_path": str(self.project_root),
            "files": [],
        }

        for item in items_to_backup:
            rel = item["dest"].relative_to(self.project_root)
            backup_dest = self.backup_dir / rel
            backup_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item["dest"], backup_dest)
            manifest["files"].append(str(rel))

        (self.backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        info["location"] = str(self.backup_dir)
        info["files"] = manifest["files"]
        return info

    def _build_next_steps(self) -> list[str]:
        """Inline the manual steps the user still has to take after auto-apply."""
        snippet_path = self.source_dir / "admin-routes.snippet.tsx"
        install_path = self.source_dir / "INSTALL.md"
        return [
            "Apply Supabase migrations: open the SQL editor in your Supabase project "
            f"and run each .sql in `{self.source_dir / 'supabase' / 'migrations'}` in order.",
            f"Promote first admin: edit and run `{self.source_dir / 'supabase' / 'set-admin.sql'}` "
            "after signing up via the app once.",
            f"Wire admin route in App.tsx: paste from `{snippet_path}`.",
            "Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in `.env.local`.",
            f"Full instructions: {install_path}",
        ]
