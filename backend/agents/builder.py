"""
Builder Agent - Generates Kirby CMS blueprints, templates, and content files
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List
from jinja2 import Template
import anthropic
from .base import BaseAgent


class BuilderAgent(BaseAgent):
    """
    Generates complete Kirby CMS structure including:
    - Blueprints (.yml files)
    - Templates (.php files)
    - Content migration scripts
    - Configuration files
    """

    def __init__(self, project_path: str, project_name: str,
                 analyzer_output: Dict[str, Any],
                 critic_output: Dict[str, Any],
                 anthropic_api_key: str = None):
        super().__init__(project_path, project_name)
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        self.analyzer_output = analyzer_output
        self.critic_output = critic_output
        self.generated_files = []
        self.output_dir = Path(project_path) / "kirby-cms-generated"

    async def execute(self) -> Dict[str, Any]:
        """Execute the builder workflow"""
        results = {
            "build_status": "pending",
            "files_generated": 0,
            "blueprints": [],
            "templates": [],
            "errors": [],
            "output_directory": str(self.output_dir)
        }

        try:
            # Step 1: Create output directory
            self.output_dir.mkdir(exist_ok=True, parents=True)
            (self.output_dir / "site" / "blueprints").mkdir(exist_ok=True, parents=True)
            (self.output_dir / "site" / "templates").mkdir(exist_ok=True, parents=True)
            (self.output_dir / "content").mkdir(exist_ok=True, parents=True)

            # Step 2: Generate blueprints for each content type
            blueprints = await self._generate_blueprints()
            results["blueprints"] = blueprints

            # Step 3: Generate templates
            templates = await self._generate_templates()
            results["templates"] = templates

            # Step 4: Generate content structure
            content_files = await self._generate_content_structure()

            # Step 5: Generate API integration (if needed)
            api_config = await self._generate_api_config()

            results["files_generated"] = len(self.generated_files)
            results["build_status"] = "completed"

        except Exception as e:
            results["build_status"] = "failed"
            results["errors"].append(str(e))
            print(f"Error in builder: {str(e)}")

        return results

    async def _generate_blueprints(self) -> List[str]:
        """Generate Kirby blueprint YAML files"""
        blueprints = []

        # Use AI recommendations if available, otherwise fall back to extracted patterns
        recommendations = self.analyzer_output.get("cms_recommendations", {})
        print(f"[Builder] AI recommendations: {list(recommendations.keys()) if recommendations else 'EMPTY'}")

        # If no AI recommendations, generate from extracted patterns
        if not recommendations:
            print("[Builder] No AI recommendations, using pattern-based fallback...")
            recommendations = await self._generate_recommendations_from_patterns()
            print(f"[Builder] Pattern-based recommendations generated: {list(recommendations.keys())}")

        for content_type, config in recommendations.items():
            try:
                blueprint_name = config.get("blueprint_name", content_type.lower())
                fields = config.get("fields", [])

                # Convert fields to Kirby format
                kirby_fields = {}
                for field in fields:
                    if isinstance(field, dict):
                        field_name = field.get("name", "")
                        field_type = self._map_field_type(field.get("type", "text"))
                        kirby_fields[field_name] = {
                            "label": field_name.replace("_", " ").title(),
                            "type": field_type,
                            "required": field.get("required", False)
                        }
                    elif isinstance(field, str):
                        kirby_fields[field] = {
                            "label": field.replace("_", " ").title(),
                            "type": "text"
                        }

                # Create blueprint structure
                blueprint = {
                    "title": content_type.title(),
                    "icon": "📄",
                    "fields": kirby_fields
                }

                # Write blueprint file
                blueprint_path = self.output_dir / "site" / "blueprints" / f"{blueprint_name}.yml"
                with open(blueprint_path, 'w') as f:
                    yaml.dump(blueprint, f, default_flow_style=False, sort_keys=False)

                self.generated_files.append(str(blueprint_path))
                blueprints.append(blueprint_name)

            except Exception as e:
                print(f"Error generating blueprint for {content_type}: {str(e)}")
                continue

        return blueprints

    async def _generate_templates(self) -> List[str]:
        """Generate Kirby PHP templates"""
        templates = []
        recommendations = self.analyzer_output.get("cms_recommendations", {})

        # If no AI recommendations, use pattern-based recommendations
        if not recommendations:
            recommendations = await self._generate_recommendations_from_patterns()

        # Create snippets directory
        snippets_dir = self.output_dir / "site" / "snippets"
        snippets_dir.mkdir(exist_ok=True, parents=True)

        # Create header snippet
        header_snippet = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= $page->title() ?> | <?= $site->title() ?></title>
    <?php if($page->description()->isNotEmpty()): ?>
    <meta name="description" content="<?= $page->description() ?>">
    <?php endif ?>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; line-height: 1.6; max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { border-bottom: 2px solid #333; margin-bottom: 2rem; padding-bottom: 1rem; }
        h1 { color: #333; }
        main { min-height: 60vh; }
        footer { margin-top: 3rem; padding-top: 2rem; border-top: 1px solid #ddd; color: #666; }
    </style>
</head>
<body>
    <header>
        <h1><a href="<?= $site->url() ?>" style="text-decoration: none; color: inherit;"><?= $site->title() ?></a></h1>
    </header>
'''
        header_path = snippets_dir / "header.php"
        with open(header_path, 'w') as f:
            f.write(header_snippet)
        self.generated_files.append(str(header_path))

        # Create footer snippet
        footer_snippet = '''    <footer>
        <p>&copy; <?= date('Y') ?> <?= $site->title() ?>. All rights reserved.</p>
    </footer>
</body>
</html>
'''
        footer_path = snippets_dir / "footer.php"
        with open(footer_path, 'w') as f:
            f.write(footer_snippet)
        self.generated_files.append(str(footer_path))

        # Create default template with full HTML
        default_template = '''<?php snippet('header') ?>

<main>
    <article>
        <h1><?= $page->title() ?></h1>
        <?php if($page->text()->isNotEmpty()): ?>
        <div class="content">
            <?= $page->text()->kirbytext() ?>
        </div>
        <?php endif ?>
    </article>
</main>

<?php snippet('footer') ?>
'''
        default_path = self.output_dir / "site" / "templates" / "default.php"
        with open(default_path, 'w') as f:
            f.write(default_template)
        self.generated_files.append(str(default_path))
        templates.append("default")

        for content_type, config in recommendations.items():
            try:
                template_name = config.get("blueprint_name", content_type.lower())
                fields = config.get("fields", [])

                # Build template content
                template_content = f'''<?php snippet('header') ?>

<article class="{template_name}">
    <h1><?= $page->title() ?></h1>
'''

                # Add fields
                for field in fields:
                    if isinstance(field, dict):
                        field_name = field.get("name", "")
                        field_type = field.get("type", "text")

                        if field_type in ["textarea", "blocks", "markdown"]:
                            template_content += f'''
    <?php if($page->{field_name}()->isNotEmpty()): ?>
    <div class="{field_name}">
        <?= $page->{field_name}()->kirbytext() ?>
    </div>
    <?php endif ?>
'''
                        elif field_type == "image":
                            template_content += f'''
    <?php if($image = $page->image()): ?>
    <img src="<?= $image->url() ?>" alt="<?= $image->alt() ?>">
    <?php endif ?>
'''
                        else:
                            template_content += f'''
    <?php if($page->{field_name}()->isNotEmpty()): ?>
    <p><?= $page->{field_name}() ?></p>
    <?php endif ?>
'''

                template_content += '''
</article>

<?php snippet('footer') ?>
'''

                # Write template file
                template_path = self.output_dir / "site" / "templates" / f"{template_name}.php"
                with open(template_path, 'w') as f:
                    f.write(template_content)

                self.generated_files.append(str(template_path))
                templates.append(template_name)

            except Exception as e:
                print(f"Error generating template for {content_type}: {str(e)}")
                continue

        return templates

    async def _generate_content_structure(self) -> List[str]:
        """Generate content directory structure for ALL content types"""
        content_files = []
        recommendations = self.analyzer_output.get("cms_recommendations", {})

        # If no AI recommendations, use pattern-based recommendations
        if not recommendations:
            recommendations = await self._generate_recommendations_from_patterns()

        # Create home page
        home_dir = self.output_dir / "content" / "home"
        home_dir.mkdir(exist_ok=True, parents=True)

        home_content = f"""Title: {self.project_name}

----

Text:

Welcome to {self.project_name}. This is your Kirby CMS powered website.

----

Description: Auto-generated Kirby CMS for {self.project_name}
"""

        home_file = home_dir / "default.txt"
        with open(home_file, 'w') as f:
            f.write(home_content)

        content_files.append(str(home_file))
        self.generated_files.append(str(home_file))

        # Create sample content for each content type
        for content_type, config in recommendations.items():
            if content_type.lower() == "pages":
                continue  # Skip generic pages, already have home

            # Get source pages for this content type
            source_pages = config.get("pages", [])
            blueprint_name = config.get("blueprint_name", content_type.lower())

            # Create a sample content item
            content_dir = self.output_dir / "content" / f"{blueprint_name}-sample"
            content_dir.mkdir(exist_ok=True, parents=True)

            # Generate content based on fields
            content_parts = [f"Title: Sample {content_type.title()}"]

            for field in config.get("fields", []):
                if isinstance(field, dict):
                    field_name = field.get("name", "")
                    field_type = field.get("type", "text")

                    if field_name.lower() not in ["title"]:  # Skip title, already added
                        content_parts.append("----")
                        content_parts.append(f"{field_name.title()}:")

                        # Generate sample content based on field type
                        if field_type in ["textarea", "markdown"]:
                            content_parts.append(f"\nThis is sample {field_name.replace('_', ' ')} content for {content_type}.")
                        else:
                            content_parts.append(f" Sample {field_name.replace('_', ' ')}")

            content_file = content_dir / f"{blueprint_name}.txt"
            with open(content_file, 'w') as f:
                f.write("\n".join(content_parts))

            content_files.append(str(content_file))
            self.generated_files.append(str(content_file))

            # Add README for this content type
            readme_content = f"""# {content_type.title()} Content Type

## Source Pages
{chr(10).join('- ' + page for page in source_pages[:5])}

## Fields
{chr(10).join('- ' + field.get('name', '') + ' (' + field.get('type', 'text') + ')' for field in config.get('fields', []) if isinstance(field, dict))}

## Usage
Edit content files in the Kirby panel or create new {content_type} entries.
"""
            readme_file = content_dir / "README.md"
            with open(readme_file, 'w') as f:
                f.write(readme_content)

            self.generated_files.append(str(readme_file))

        return content_files

    async def _generate_api_config(self) -> Dict[str, Any]:
        """Generate API configuration if data sources were detected"""
        api_config = {
            "enabled": False,
            "endpoints": []
        }

        data_sources = self.analyzer_output.get("data_sources", [])
        if data_sources:
            api_config["enabled"] = True
            # Generate REST API endpoints configuration
            # This would be project-specific

        return api_config

    async def _generate_recommendations_from_patterns(self) -> Dict[str, Any]:
        """Generate CMS recommendations from extracted patterns when AI recommendations are missing"""
        recommendations = {}
        extracted_patterns = self.analyzer_output.get("extracted_patterns", {})

        # Analyze patterns to detect content types
        content_types = self._detect_content_types_from_patterns(extracted_patterns)

        for content_type, pages in content_types.items():
            # Aggregate common fields from all pages of this type
            common_fields = self._extract_common_fields(pages, extracted_patterns)

            recommendations[content_type] = {
                "description": f"{content_type.title()} content type",
                "fields": common_fields,
                "blueprint_name": content_type.lower().replace(" ", "_"),
                "pages": [p for p in pages]  # Track source pages
            }

        return recommendations

    def _detect_content_types_from_patterns(self, patterns: Dict) -> Dict[str, List[str]]:
        """Detect content types from URL patterns and content structure"""
        content_types = {
            "pages": [],
            "locations": [],
            "programs": [],
            "services": [],
            "blog": [],
            "team": []
        }

        for filename, data in patterns.items():
            if not isinstance(data, dict):
                continue

            title = (data.get("title") or "").lower()
            path = (data.get("path") or filename).lower()
            headings = data.get("headings", {})

            # Location detection
            if any(keyword in path or keyword in title for keyword in ["location", "downtown", "north-", "cary", "apex", "wake-forest", "address"]):
                content_types["locations"].append(filename)
            # Programs/Training detection
            elif any(keyword in path or keyword in title for keyword in ["program", "training", "clinic", "group-training", "team-training"]):
                content_types["programs"].append(filename)
            # Services detection
            elif any(keyword in path or keyword in title for keyword in ["service", "offering", "what-we-do"]):
                content_types["services"].append(filename)
            # Blog detection
            elif any(keyword in path or keyword in title for keyword in ["blog", "post", "article", "news"]):
                content_types["blog"].append(filename)
            # Team detection
            elif any(keyword in path or keyword in title for keyword in ["team", "staff", "coach", "about-us"]):
                content_types["team"].append(filename)
            # Default to pages
            else:
                content_types["pages"].append(filename)

        # Remove empty content types
        return {k: v for k, v in content_types.items() if v}

    def _extract_common_fields(self, page_list: List[str], patterns: Dict) -> List[Dict]:
        """Extract common fields from a list of similar pages"""
        fields = [
            {"name": "title", "type": "text", "required": True},
            {"name": "description", "type": "textarea", "required": False}
        ]

        # Analyze first page to detect field patterns
        if page_list and page_list[0] in patterns:
            page_data = patterns[page_list[0]]

            # Check for images
            if page_data.get("images", []):
                fields.append({"name": "featured_image", "type": "files", "required": False})

            # Check for substantial content
            if page_data.get("paragraphs", []):
                fields.append({"name": "content", "type": "textarea", "required": False})

            # Check for headings (indicates structured content)
            if page_data.get("headings", {}).get("h2", []):
                fields.append({"name": "sections", "type": "textarea", "required": False})

            # Check for meta description
            if page_data.get("meta_description"):
                fields.append({"name": "meta_description", "type": "text", "required": False})

        return fields

    def _map_field_type(self, field_type: str) -> str:
        """Map generic field types to Kirby field types"""
        mapping = {
            "text": "text",
            "textarea": "textarea",
            "wysiwyg": "textarea",
            "markdown": "markdown",
            "number": "number",
            "email": "email",
            "url": "url",
            "date": "date",
            "time": "time",
            "select": "select",
            "checkbox": "toggle",
            "image": "files",
            "file": "files",
            "files": "files",
            "gallery": "files",
            "tags": "tags",
            "toggle": "toggle",
            "radio": "radio"
        }
        return mapping.get(field_type.lower(), "text")
