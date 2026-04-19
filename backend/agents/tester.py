"""
Tester Agent - Validates generated Kirby CMS files
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List
from .base import BaseAgent


class TesterAgent(BaseAgent):
    """
    Tests the generated Kirby CMS structure for:
    - Syntax validation (YAML, PHP)
    - File integrity
    - Blueprint completeness
    - Template correctness
    """

    def __init__(self, project_path: str, project_name: str, builder_output: Dict[str, Any]):
        super().__init__(project_path, project_name)
        self.builder_output = builder_output
        self.output_dir = Path(builder_output.get("output_directory", ""))

    async def execute(self) -> Dict[str, Any]:
        """Execute the testing workflow"""
        results = {
            "test_status": "pending",
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": [],
            "warnings": [],
            "validation_details": {}
        }

        try:
            # Step 1: Validate YAML syntax
            yaml_results = await self._validate_yaml_files()
            results["validation_details"]["yaml"] = yaml_results
            results["tests_run"] += yaml_results["total"]
            results["tests_passed"] += yaml_results["passed"]
            results["tests_failed"] += yaml_results["failed"]

            # Step 2: Validate PHP syntax
            php_results = await self._validate_php_files()
            results["validation_details"]["php"] = php_results
            results["tests_run"] += php_results["total"]
            results["tests_passed"] += php_results["passed"]
            results["tests_failed"] += php_results["failed"]

            # Step 3: Check file structure
            structure_results = await self._validate_structure()
            results["validation_details"]["structure"] = structure_results
            results["tests_run"] += structure_results["total"]
            results["tests_passed"] += structure_results["passed"]
            results["tests_failed"] += structure_results["failed"]

            # Step 4: Validate content
            content_results = await self._validate_content()
            results["validation_details"]["content"] = content_results
            results["tests_run"] += content_results["total"]
            results["tests_passed"] += content_results["passed"]
            results["tests_failed"] += content_results["failed"]

            # Determine overall status
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
            print(f"Error in tester: {str(e)}")

        return results

    async def _validate_yaml_files(self) -> Dict[str, Any]:
        """Validate YAML blueprint files"""
        result = {"total": 0, "passed": 0, "failed": 0, "errors": []}

        blueprints_dir = self.output_dir / "site" / "blueprints"
        if not blueprints_dir.exists():
            result["errors"].append("Blueprints directory not found")
            return result

        for yaml_file in blueprints_dir.glob("*.yml"):
            result["total"] += 1
            try:
                with open(yaml_file, 'r') as f:
                    blueprint = yaml.safe_load(f)

                # Check required fields
                if not isinstance(blueprint, dict):
                    raise ValueError("Blueprint must be a dictionary")

                if "title" not in blueprint:
                    raise ValueError("Blueprint missing 'title' field")

                if "fields" not in blueprint or not isinstance(blueprint["fields"], dict):
                    raise ValueError("Blueprint missing or invalid 'fields' section")

                result["passed"] += 1

            except Exception as e:
                result["failed"] += 1
                result["errors"].append(f"{yaml_file.name}: {str(e)}")

        return result

    async def _validate_php_files(self) -> Dict[str, Any]:
        """Validate PHP template files"""
        result = {"total": 0, "passed": 0, "failed": 0, "errors": []}

        templates_dir = self.output_dir / "site" / "templates"
        if not templates_dir.exists():
            result["errors"].append("Templates directory not found")
            return result

        for php_file in templates_dir.glob("*.php"):
            result["total"] += 1
            try:
                with open(php_file, 'r') as f:
                    content = f.read()

                # Basic PHP syntax checks
                if not content.strip():
                    raise ValueError("Template file is empty")

                # Check for basic PHP tags
                if "<?php" not in content and "<?=" not in content:
                    raise ValueError("No PHP code found in template")

                # Check for balanced brackets (simple validation)
                open_count = content.count("<?php") + content.count("<?=")
                close_count = content.count("?>")
                if open_count > 0 and close_count > 0 and open_count != close_count:
                    result["errors"].append(f"{php_file.name}: Warning - Unbalanced PHP tags")

                result["passed"] += 1

            except Exception as e:
                result["failed"] += 1
                result["errors"].append(f"{php_file.name}: {str(e)}")

        return result

    async def _validate_structure(self) -> Dict[str, Any]:
        """Validate directory structure"""
        result = {"total": 0, "passed": 0, "failed": 0, "errors": []}

        required_dirs = [
            "site/blueprints",
            "site/templates",
            "content"
        ]

        for dir_path in required_dirs:
            result["total"] += 1
            full_path = self.output_dir / dir_path
            if full_path.exists() and full_path.is_dir():
                result["passed"] += 1
            else:
                result["failed"] += 1
                result["errors"].append(f"Missing required directory: {dir_path}")

        return result

    async def _validate_content(self) -> Dict[str, Any]:
        """Validate content files"""
        result = {"total": 0, "passed": 0, "failed": 0, "errors": []}

        content_dir = self.output_dir / "content"
        if not content_dir.exists():
            result["errors"].append("Content directory not found")
            return result

        # Check for at least one content file
        txt_files = list(content_dir.glob("**/*.txt"))
        result["total"] = 1

        if len(txt_files) > 0:
            result["passed"] = 1

            # Validate content file format
            for txt_file in txt_files:
                try:
                    with open(txt_file, 'r') as f:
                        content = f.read()

                    # Basic Kirby content file validation
                    if "Title:" not in content:
                        result["errors"].append(f"{txt_file.name}: Missing Title field")

                except Exception as e:
                    result["errors"].append(f"{txt_file.name}: {str(e)}")
        else:
            result["failed"] = 1
            result["errors"].append("No content files found")

        return result
