"""
Applicator Agent - Safely applies CMS changes to the project
"""
import os
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from .base import BaseAgent


class ApplicatorAgent(BaseAgent):
    """
    Applies generated Kirby CMS files to the project with:
    - Backup system
    - Safe integration
    - Rollback mechanism
    - Verification
    """

    def __init__(self, project_path: str, project_name: str,
                 builder_output: Dict[str, Any],
                 tester_output: Dict[str, Any],
                 auto_apply: bool = False):
        super().__init__(project_path, project_name)
        self.builder_output = builder_output
        self.tester_output = tester_output
        self.auto_apply = auto_apply
        self.source_dir = Path(builder_output.get("output_directory", ""))
        self.backup_dir = None
        self.applied_files = []

    async def execute(self) -> Dict[str, Any]:
        """Execute the application workflow"""
        results = {
            "apply_status": "pending",
            "backup_created": False,
            "backup_location": None,
            "files_applied": 0,
            "rollback_available": False,
            "errors": [],
            "warnings": []
        }

        try:
            # Step 0: Check if tests passed
            if self.tester_output.get("test_status") not in ["passed", "passed_with_warnings"]:
                results["apply_status"] = "skipped"
                results["errors"].append("Cannot apply: Tests did not pass")
                return results

            # Step 1: Create backup
            backup_result = await self._create_backup()
            results["backup_created"] = backup_result["success"]
            results["backup_location"] = backup_result.get("location")
            results["rollback_available"] = backup_result["success"]

            if not backup_result["success"]:
                results["errors"].append("Backup failed - aborting application")
                results["apply_status"] = "failed"
                return results

            # Step 2: Check if auto-apply is enabled
            if not self.auto_apply:
                results["apply_status"] = "awaiting_approval"
                results["warnings"].append("Auto-apply disabled - manual approval required")
                return results

            # Step 3: Apply files
            apply_result = await self._apply_files()
            results["files_applied"] = apply_result["count"]
            self.applied_files = apply_result["files"]

            if apply_result["errors"]:
                results["errors"].extend(apply_result["errors"])
                # Rollback on error
                rollback_result = await self._rollback()
                results["apply_status"] = "failed_rolled_back"
                return results

            # Step 4: Verify application
            verification = await self._verify_application()
            results["verification"] = verification

            if verification["success"]:
                results["apply_status"] = "completed"
            else:
                results["apply_status"] = "completed_with_warnings"
                results["warnings"].extend(verification["warnings"])

        except Exception as e:
            results["apply_status"] = "error"
            results["errors"].append(str(e))
            print(f"Error in applicator: {str(e)}")

            # Attempt rollback
            if self.backup_dir:
                await self._rollback()
                results["apply_status"] = "error_rolled_back"

        return results

    async def _create_backup(self) -> Dict[str, Any]:
        """Create a backup of the current project state"""
        result = {"success": False, "location": None}

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.backup_dir = Path(self.project_path) / ".kirby-backups" / f"backup_{timestamp}"
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            # Create backup manifest
            manifest = {
                "timestamp": timestamp,
                "project_name": self.project_name,
                "project_path": self.project_path,
                "files_backed_up": []
            }

            # Backup existing kirby-cms-generated directory if it exists
            existing_cms = Path(self.project_path) / "kirby-cms-generated"
            if existing_cms.exists():
                backup_cms = self.backup_dir / "kirby-cms-generated"
                shutil.copytree(existing_cms, backup_cms)
                manifest["files_backed_up"].append(str(existing_cms))

            # Save manifest
            manifest_file = self.backup_dir / "manifest.json"
            with open(manifest_file, 'w') as f:
                json.dump(manifest, f, indent=2)

            result["success"] = True
            result["location"] = str(self.backup_dir)

        except Exception as e:
            print(f"Backup error: {str(e)}")
            result["error"] = str(e)

        return result

    async def _apply_files(self) -> Dict[str, Any]:
        """Apply generated files to the project"""
        result = {"count": 0, "files": [], "errors": []}

        try:
            # The files are already in kirby-cms-generated
            # We just need to verify they're in place

            if not self.source_dir.exists():
                result["errors"].append(f"Source directory not found: {self.source_dir}")
                return result

            # Count and track applied files
            for file_path in self.source_dir.rglob("*"):
                if file_path.is_file():
                    result["count"] += 1
                    result["files"].append(str(file_path))

            # Create a README in the generated directory
            readme_path = self.source_dir / "README.md"
            readme_content = f"""# Kirby CMS - Auto-Generated

**Project:** {self.project_name}
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## What's Included

- `site/blueprints/` - Content type definitions
- `site/templates/` - PHP templates for each content type
- `content/` - Initial content structure

## Next Steps

1. Copy a complete Kirby installation to this directory
2. Merge the generated files with your Kirby setup
3. Access the Kirby Panel at `/panel`
4. Start managing your content!

## Integration

To integrate with your existing frontend:

1. Use Kirby's REST API to fetch content
2. Update your frontend components to consume CMS data
3. Remove hardcoded content from your components

## Backup

A backup was created at:
`{self.backup_dir}`

You can restore using the rollback feature if needed.
"""

            with open(readme_path, 'w') as f:
                f.write(readme_content)

            result["count"] += 1
            result["files"].append(str(readme_path))

        except Exception as e:
            result["errors"].append(str(e))

        return result

    async def _verify_application(self) -> Dict[str, Any]:
        """Verify that files were applied correctly"""
        result = {"success": True, "warnings": []}

        try:
            # Check that key directories exist
            required_dirs = [
                self.source_dir / "site" / "blueprints",
                self.source_dir / "site" / "templates",
                self.source_dir / "content"
            ]

            for dir_path in required_dirs:
                if not dir_path.exists():
                    result["success"] = False
                    result["warnings"].append(f"Missing directory: {dir_path}")

            # Check that files were created
            if not self.applied_files:
                result["success"] = False
                result["warnings"].append("No files were applied")

        except Exception as e:
            result["success"] = False
            result["warnings"].append(str(e))

        return result

    async def _rollback(self) -> Dict[str, Any]:
        """Rollback changes using backup"""
        result = {"success": False, "message": ""}

        try:
            if not self.backup_dir or not self.backup_dir.exists():
                result["message"] = "No backup available for rollback"
                return result

            # Read manifest
            manifest_file = self.backup_dir / "manifest.json"
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)

            # Restore backed up files
            cms_dir = Path(self.project_path) / "kirby-cms-generated"
            if cms_dir.exists():
                shutil.rmtree(cms_dir)

            backup_cms = self.backup_dir / "kirby-cms-generated"
            if backup_cms.exists():
                shutil.copytree(backup_cms, cms_dir)

            result["success"] = True
            result["message"] = f"Rollback successful from {self.backup_dir}"

        except Exception as e:
            result["message"] = f"Rollback failed: {str(e)}"

        return result
