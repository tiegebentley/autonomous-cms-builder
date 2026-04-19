"""
Analyzer Agent - Scans frontend projects and extracts content patterns
"""
import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
import anthropic
from .base import BaseAgent


class AnalyzerAgent(BaseAgent):
    """
    Analyzes frontend projects to identify content patterns
    that should be managed via CMS.

    Supports:
    - Static HTML
    - React (Vite, CRA)
    - Next.js (Pages & App Router)
    - Vite projects
    """

    def __init__(self, project_path: str, project_name: str, anthropic_api_key: str = None):
        super().__init__(project_path, project_name)
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        self.html_files = []
        self.component_files = []
        self.extracted_content = {}
        self.framework = None
        self.package_json = None

    async def execute(self) -> Dict[str, Any]:
        """Execute the analysis workflow"""
        results = {
            "project_path": self.project_path,
            "project_name": self.project_name,
            "framework": None,
            "files_analyzed": 0,
            "components_analyzed": 0,
            "content_types_found": [],
            "cms_recommendations": {},
            "extracted_patterns": {},
            "routes": [],
            "data_sources": []
        }

        # Step 1: Detect framework
        await self._detect_framework()
        results["framework"] = self.framework

        # Step 2: Scan for files based on framework
        if self.framework in ["react", "nextjs", "vite"]:
            await self._scan_component_files()
            results["components_analyzed"] = len(self.component_files)
            await self._extract_component_patterns()
        else:
            # Fallback to HTML analysis for static sites
            await self._scan_html_files()
            results["files_analyzed"] = len(self.html_files)
            await self._extract_content_patterns()

        # Step 3: Extract routes
        await self._extract_routes()
        results["routes"] = self.extracted_content.get("routes", [])

        # Step 4: Detect content types from patterns (rule-based)
        detected_types = await self._detect_content_types_from_patterns()
        results["content_types_found"] = list(detected_types.keys())

        # Step 5: Use AI to enhance analysis (optional)
        ai_analysis = await self._analyze_with_ai()

        # Merge AI recommendations with rule-based detection
        ai_recommendations = ai_analysis.get("recommendations", {})
        if ai_recommendations:
            results["cms_recommendations"] = ai_recommendations
        else:
            # Use rule-based recommendations if AI fails
            results["cms_recommendations"] = detected_types

        results["data_sources"] = ai_analysis.get("data_sources", [])
        results["extracted_patterns"] = self.extracted_content

        return results

    async def _scan_html_files(self) -> None:
        """Scan project directory for HTML files"""
        project_path = Path(self.project_path)

        if not project_path.exists():
            raise FileNotFoundError(f"Project path does not exist: {self.project_path}")

        # Find all HTML files
        self.html_files = list(project_path.glob("**/*.html"))

        # Exclude common directories
        exclude_dirs = {'.git', 'node_modules', 'dist', 'build', '.next'}
        self.html_files = [
            f for f in self.html_files
            if not any(exc in f.parts for exc in exclude_dirs)
        ]

    async def _extract_content_patterns(self) -> None:
        """Extract content from HTML files using BeautifulSoup"""
        for html_file in self.html_files:
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                soup = BeautifulSoup(content, 'html.parser')

                # Extract key content elements
                file_data = {
                    "path": str(html_file.relative_to(self.project_path)),
                    "title": soup.title.string if soup.title else None,
                    "headings": {
                        "h1": [h.get_text(strip=True) for h in soup.find_all('h1')],
                        "h2": [h.get_text(strip=True) for h in soup.find_all('h2')],
                        "h3": [h.get_text(strip=True) for h in soup.find_all('h3')],
                    },
                    "images": [
                        {"src": img.get('src'), "alt": img.get('alt')}
                        for img in soup.find_all('img')
                    ],
                    "links": [
                        {"href": a.get('href'), "text": a.get_text(strip=True)}
                        for a in soup.find_all('a')
                    ],
                    "paragraphs": [p.get_text(strip=True) for p in soup.find_all('p')][:5],  # First 5 paragraphs
                    "meta_description": None
                }

                # Extract meta description
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    file_data["meta_description"] = meta_desc.get('content')

                self.extracted_content[str(html_file.name)] = file_data

            except Exception as e:
                print(f"Error parsing {html_file}: {str(e)}")
                continue

    async def _detect_content_types_from_patterns(self) -> Dict[str, Any]:
        """
        Detect content types from extracted patterns using rules.
        This provides a fallback when AI analysis fails.
        """
        content_types = {}

        # Analyze each file and categorize
        categories = {
            "locations": [],
            "programs": [],
            "services": [],
            "blog": [],
            "team": [],
            "pages": []
        }

        for filename, data in self.extracted_content.items():
            if filename in ['routes', 'components']:
                continue

            if not isinstance(data, dict):
                continue

            title = (data.get("title") or "").lower()
            path = (data.get("path") or filename).lower()

            # Location detection (improved patterns)
            if any(keyword in path or keyword in title for keyword in [
                "location", "downtown", "north-", "south-", "east-", "west-",
                "cary", "apex", "wake-forest", "durham", "chapel-hill",
                "address", "where-we-are", "find-us", "directions"
            ]):
                categories["locations"].append(filename)

            # Programs/Services detection
            elif any(keyword in path or keyword in title for keyword in [
                "program", "training", "clinic", "class", "course",
                "group-training", "team-training", "lesson", "workshop"
            ]):
                categories["programs"].append(filename)

            # Services detection
            elif any(keyword in path or keyword in title for keyword in [
                "service", "offering", "what-we-do", "solutions", "packages"
            ]):
                categories["services"].append(filename)

            # Blog detection
            elif any(keyword in path or keyword in title for keyword in [
                "blog", "post", "article", "news", "update", "press"
            ]):
                categories["blog"].append(filename)

            # Team detection
            elif any(keyword in path or keyword in title for keyword in [
                "team", "staff", "coach", "about-us", "who-we-are", "people"
            ]):
                categories["team"].append(filename)

            # Default to pages
            else:
                categories["pages"].append(filename)

        # Generate recommendations for each non-empty category
        for category, files in categories.items():
            if not files:
                continue

            # Analyze first file to determine fields
            sample_file = files[0] if files else None
            fields = self._generate_fields_for_type(category, sample_file)

            content_types[category] = {
                "description": f"{category.title()} content type",
                "fields": fields,
                "blueprint_name": category.lower().replace(" ", "_"),
                "page_count": len(files),
                "sample_pages": files[:5]  # First 5 as examples
            }

        return content_types

    def _generate_fields_for_type(self, content_type: str, sample_file: Optional[str] = None) -> List[Dict]:
        """Generate appropriate fields based on content type"""
        # Base fields for all types
        fields = [
            {"name": "title", "type": "text", "required": True},
            {"name": "description", "type": "textarea", "required": False}
        ]

        # Type-specific fields
        if content_type == "locations":
            fields.extend([
                {"name": "address", "type": "text", "required": False},
                {"name": "city", "type": "text", "required": False},
                {"name": "state", "type": "text", "required": False},
                {"name": "zip_code", "type": "text", "required": False},
                {"name": "phone", "type": "text", "required": False},
                {"name": "email", "type": "email", "required": False},
                {"name": "map_embed", "type": "textarea", "required": False}
            ])
        elif content_type == "programs":
            fields.extend([
                {"name": "program_type", "type": "text", "required": False},
                {"name": "duration", "type": "text", "required": False},
                {"name": "price", "type": "text", "required": False},
                {"name": "schedule", "type": "textarea", "required": False},
                {"name": "features", "type": "textarea", "required": False}
            ])
        elif content_type == "blog":
            fields.extend([
                {"name": "author", "type": "text", "required": False},
                {"name": "publish_date", "type": "date", "required": False},
                {"name": "featured_image", "type": "files", "required": False},
                {"name": "excerpt", "type": "textarea", "required": False},
                {"name": "tags", "type": "tags", "required": False}
            ])
        elif content_type == "team":
            fields.extend([
                {"name": "role", "type": "text", "required": False},
                {"name": "bio", "type": "textarea", "required": False},
                {"name": "photo", "type": "files", "required": False},
                {"name": "email", "type": "email", "required": False},
                {"name": "linkedin", "type": "url", "required": False}
            ])

        # Check sample file for additional patterns
        if sample_file and sample_file in self.extracted_content:
            sample_data = self.extracted_content[sample_file]

            # Add image field if images found
            if sample_data.get("images", []):
                fields.append({"name": "featured_image", "type": "files", "required": False})

            # Add content field if paragraphs found
            if sample_data.get("paragraphs", []):
                fields.append({"name": "content", "type": "textarea", "required": False})

            # Add meta description if found
            if sample_data.get("meta_description"):
                fields.append({"name": "meta_description", "type": "text", "required": False})

        return fields

    async def _analyze_with_ai(self) -> Dict[str, Any]:
        """Use Claude AI to analyze content patterns and recommend CMS structure"""

        # Prepare content summary for AI analysis
        content_summary = self._prepare_content_summary()

        # Prepare routes and framework info
        routes_info = self.extracted_content.get("routes", [])
        framework_info = self.framework or "static"

        prompt = f"""You are analyzing a frontend project to design a Kirby CMS structure.

Project: {self.project_name}
Framework: {framework_info}
Files analyzed: {len(self.html_files) + len(self.component_files)}
Routes found: {', '.join(routes_info[:10]) if routes_info else 'None detected'}

Content Summary:
{content_summary}

Please analyze this {framework_info} project and provide:
1. What content types are present (e.g., pages, blog posts, locations, services, team members)
2. What content should be managed via CMS (vs hardcoded UI elements)
3. Recommended Kirby CMS blueprint structure
4. Suggested field types for each content type
5. Data sources identified (API calls, static data, etc.)

Respond in JSON format with:
{{
  "content_types": ["type1", "type2"],
  "data_sources": ["where the content currently comes from"],
  "recommendations": {{
    "type1": {{
      "description": "what this content type represents",
      "fields": [
        {{"name": "field1", "type": "text", "required": true}},
        {{"name": "field2", "type": "textarea", "required": false}}
      ],
      "blueprint_name": "suggested_blueprint_name"
    }}
  }},
  "cms_managed": ["list of content that should be CMS-managed"],
  "hardcoded": ["list of content that should stay hardcoded (navigation, footer, UI elements)"]
}}
"""

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract JSON from response
            response_text = message.content[0].text

            # Try to parse JSON from response
            import json
            import re

            # Look for JSON block in markdown or plain text
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                json_str = json_match.group(0) if json_match else response_text

            ai_response = json.loads(json_str)
            return ai_response

        except Exception as e:
            print(f"Error in AI analysis: {str(e)}")
            return {
                "content_types": ["pages"],
                "recommendations": {},
                "error": str(e)
            }

    def _prepare_content_summary(self) -> str:
        """Prepare a concise summary of extracted content for AI analysis"""
        summary_parts = []

        summary_parts.append(f"Framework: {self.framework or 'static'}")
        summary_parts.append(f"Total files: {len(self.extracted_content)}")

        for filename, data in self.extracted_content.items():
            if filename in ['routes', 'components']:
                continue

            summary_parts.append(f"\n--- {filename} ---")

            # Handle component data
            if isinstance(data, dict) and 'type' in data and data['type'] == 'component':
                summary_parts.append(f"Type: React Component")
                summary_parts.append(f"JSX Elements: {', '.join(data.get('jsx_elements', [])[:5])}")
                summary_parts.append(f"Text Content: {data.get('text_content', '')[:100]}...")
            else:
                # Handle HTML data
                summary_parts.append(f"Title: {data.get('title', 'N/A')}")
                summary_parts.append(f"H1 Headings: {', '.join(data['headings']['h1'][:3]) if data.get('headings', {}).get('h1') else 'None'}")
                summary_parts.append(f"H2 Headings: {', '.join(data['headings']['h2'][:3]) if data.get('headings', {}).get('h2') else 'None'}")
                summary_parts.append(f"Images: {len(data.get('images', []))} found")
                summary_parts.append(f"Links: {len(data.get('links', []))} found")

        return "\n".join(summary_parts[:500])  # Limit to first 500 lines

    async def _detect_framework(self) -> None:
        """Detect the framework used in the project"""
        project_path = Path(self.project_path)
        package_json_path = project_path / "package.json"

        if not package_json_path.exists():
            self.framework = "static"
            return

        try:
            with open(package_json_path, 'r') as f:
                self.package_json = json.load(f)

            dependencies = {
                **self.package_json.get("dependencies", {}),
                **self.package_json.get("devDependencies", {})
            }

            # Check for Next.js
            if "next" in dependencies:
                self.framework = "nextjs"
            # Check for React + Vite
            elif "vite" in dependencies and "react" in dependencies:
                self.framework = "vite"
            # Check for React (CRA or other)
            elif "react" in dependencies:
                self.framework = "react"
            else:
                self.framework = "static"

        except Exception as e:
            print(f"Error detecting framework: {str(e)}")
            self.framework = "static"

    async def _scan_component_files(self) -> None:
        """Scan project directory for React/JSX/TSX files"""
        project_path = Path(self.project_path)

        if not project_path.exists():
            raise FileNotFoundError(f"Project path does not exist: {self.project_path}")

        # Find all component files
        patterns = ["**/*.jsx", "**/*.tsx", "**/*.js", "**/*.ts"]
        self.component_files = []

        for pattern in patterns:
            self.component_files.extend(project_path.glob(pattern))

        # Exclude common directories
        exclude_dirs = {'.git', 'node_modules', 'dist', 'build', '.next', 'out', 'coverage', 'venv'}
        self.component_files = [
            f for f in self.component_files
            if not any(exc in f.parts for exc in exclude_dirs)
        ]

        # Filter to only files that likely contain React components
        # (check for JSX syntax or React imports)
        valid_components = []
        for file_path in self.component_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Check for React patterns
                    if any(pattern in content for pattern in ['import React', 'from "react"', 'from \'react\'', '<div', '<section', '<main']):
                        valid_components.append(file_path)
            except:
                continue

        self.component_files = valid_components[:50]  # Limit to first 50 components

    async def _extract_component_patterns(self) -> None:
        """Extract content patterns from React components"""
        for component_file in self.component_files:
            try:
                with open(component_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract JSX elements (simple regex-based approach)
                jsx_elements = re.findall(r'<(\w+)[^>]*>', content)

                # Extract string literals (potential content)
                string_content = re.findall(r'["\']([^"\']{10,})["\']', content)

                # Extract className values (might indicate UI patterns)
                classnames = re.findall(r'className=["\']([^"\']+)["\']', content)

                # Extract image sources
                images = re.findall(r'src=["\']([^"\']+\.(jpg|png|svg|webp))["\']', content)

                file_data = {
                    "type": "component",
                    "path": str(component_file.relative_to(self.project_path)),
                    "jsx_elements": list(set(jsx_elements))[:20],
                    "text_content": " ".join(string_content[:10]),
                    "classnames": list(set(classnames))[:10],
                    "images": [img[0] for img in images],
                    "has_state": "useState" in content or "useReducer" in content,
                    "has_effects": "useEffect" in content,
                    "has_api_calls": "fetch(" in content or "axios." in content or "api." in content
                }

                self.extracted_content[str(component_file.name)] = file_data

            except Exception as e:
                print(f"Error parsing component {component_file}: {str(e)}")
                continue

    async def _extract_routes(self) -> None:
        """Extract routes from the project"""
        project_path = Path(self.project_path)
        routes = []

        if self.framework == "nextjs":
            # Next.js Pages Router
            pages_dir = project_path / "pages"
            if pages_dir.exists():
                page_files = list(pages_dir.glob("**/*.{js,jsx,ts,tsx}"))
                for page in page_files:
                    route = str(page.relative_to(pages_dir)).replace("\\", "/")
                    route = route.replace(".tsx", "").replace(".jsx", "").replace(".ts", "").replace(".js", "")
                    if route == "index":
                        route = "/"
                    elif not route.startswith("_"):
                        route = f"/{route}"
                        routes.append(route)

            # Next.js App Router
            app_dir = project_path / "app"
            if app_dir.exists():
                page_files = list(app_dir.glob("**/page.{js,jsx,ts,tsx}"))
                for page in page_files:
                    route = str(page.parent.relative_to(app_dir)).replace("\\", "/")
                    route = f"/{route}" if route != "." else "/"
                    routes.append(route)

        elif self.framework in ["react", "vite"]:
            # Try to find router configuration
            router_files = list(project_path.glob("**/*{router,routes,Router,Routes}*.{js,jsx,ts,tsx}"))
            for router_file in router_files[:3]:  # Check first 3 router files
                try:
                    with open(router_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Extract route paths
                        route_patterns = re.findall(r'path=["\']([^"\']+)["\']', content)
                        routes.extend(route_patterns)
                except:
                    continue

        self.extracted_content["routes"] = list(set(routes))
