"""
Installer Agent - Automatically downloads and installs Kirby CMS

This agent:
1. Detects if Kirby is already installed
2. Downloads Kirby CMS if needed
3. Installs to project/kirby/ directory
4. Configures basic settings
5. Prepares for file integration
"""
import os
import shutil
import subprocess
import json
from typing import Dict, Any, Optional
from datetime import datetime
from .base import BaseAgent


class InstallerAgent:
    """Agent responsible for Kirby CMS installation (standalone, not inheriting BaseAgent)"""

    def __init__(self):
        self.name = "installer"
        self.icon = "📦"
        self.kirby_starterkit_url = "https://github.com/getkirby/starterkit/archive/refs/heads/main.zip"
        self.kirby_plainkit_url = "https://github.com/getkirby/plainkit/archive/refs/heads/main.zip"
        self.logs = []

    def log(self, message: str, level: str = "info"):
        """Log a message"""
        self.logs.append({"message": message, "level": level})
        print(f"[{self.name}] {message}")

    async def execute(self, project_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Install or detect Kirby CMS in the project

        Args:
            project_path: Path to the project
            options: Installation options
                - force_reinstall: bool - Reinstall even if exists
                - use_starterkit: bool - Use starterkit (default: plainkit)

        Returns:
            Installation result with kirby_path and status
        """
        try:
            self.log("Starting Kirby CMS installation check...")

            # Check if Kirby already exists
            existing_kirby = self._detect_existing_kirby(project_path)

            if existing_kirby and not options.get('force_reinstall', False):
                self.log(f"✅ Found existing Kirby installation at: {existing_kirby}")
                return {
                    'success': True,
                    'action': 'detected',
                    'kirby_path': existing_kirby,
                    'message': 'Using existing Kirby installation',
                    'is_new': False
                }

            # Install new Kirby
            self.log("No Kirby found. Installing fresh instance...")
            kirby_path = await self._install_kirby(project_path, options)

            self.log(f"✅ Kirby installed successfully at: {kirby_path}")
            return {
                'success': True,
                'action': 'installed',
                'kirby_path': kirby_path,
                'message': 'Kirby CMS installed successfully',
                'is_new': True
            }

        except Exception as e:
            self.log(f"❌ Installation failed: {str(e)}", level="error")
            raise Exception(f"Kirby installation failed: {str(e)}")

    def _detect_existing_kirby(self, project_path: str) -> Optional[str]:
        """
        Detect if Kirby is already installed in the project

        Looks for:
        - kirby/ folder with kirby/index.php
        - site/ and content/ folders
        """
        possible_paths = [
            os.path.join(project_path, 'kirby'),
            os.path.join(project_path, 'kirby-cms'),
            project_path  # Root level Kirby
        ]

        for path in possible_paths:
            if self._is_kirby_installation(path):
                return path

        return None

    def _is_kirby_installation(self, path: str) -> bool:
        """Check if path contains a valid Kirby installation"""
        if not os.path.exists(path):
            return False

        # Check for Kirby core files
        kirby_index = os.path.join(path, 'kirby', 'index.php')
        site_folder = os.path.join(path, 'site')
        content_folder = os.path.join(path, 'content')

        return (
            os.path.exists(kirby_index) and
            os.path.isdir(site_folder) and
            os.path.isdir(content_folder)
        )

    async def _install_kirby(self, project_path: str, options: Optional[Dict[str, Any]] = None) -> str:
        """
        Download and install Kirby CMS

        Args:
            project_path: Where to install Kirby
            options: Installation options

        Returns:
            Path to installed Kirby
        """
        use_starterkit = options.get('use_starterkit', False) if options else False
        download_url = self.kirby_starterkit_url if use_starterkit else self.kirby_plainkit_url

        # Determine installation path
        kirby_install_path = os.path.join(project_path, 'kirby')

        self.log(f"Installing Kirby to: {kirby_install_path}")

        # Create temp directory for download
        temp_dir = os.path.join(project_path, '.kirby-temp')
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # Download Kirby
            zip_path = os.path.join(temp_dir, 'kirby.zip')
            self.log("Downloading Kirby CMS...")

            subprocess.run(
                ['wget', '-q', '-O', zip_path, download_url],
                check=True,
                capture_output=True
            )

            # Extract
            self.log("Extracting Kirby files...")
            subprocess.run(
                ['unzip', '-q', '-o', zip_path, '-d', temp_dir],
                check=True,
                capture_output=True
            )

            # Find extracted folder (usually plainkit-main or starterkit-main)
            extracted_folders = [f for f in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, f))]
            if not extracted_folders:
                raise Exception("Failed to extract Kirby files")

            extracted_path = os.path.join(temp_dir, extracted_folders[0])

            # Move to final location
            self.log(f"Moving files to {kirby_install_path}...")
            if os.path.exists(kirby_install_path):
                shutil.rmtree(kirby_install_path)

            shutil.move(extracted_path, kirby_install_path)

            # Set permissions
            self.log("Setting permissions...")
            subprocess.run(
                ['chmod', '-R', '755', kirby_install_path],
                check=True
            )

            # Create .htaccess if doesn't exist
            self._create_htaccess(kirby_install_path)

            self.log("✅ Kirby installation complete!")
            return kirby_install_path

        finally:
            # Cleanup temp directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def _create_htaccess(self, kirby_path: str):
        """Create basic .htaccess for Kirby"""
        htaccess_path = os.path.join(kirby_path, '.htaccess')

        if os.path.exists(htaccess_path):
            return

        htaccess_content = """# Kirby .htaccess

# Rewrite rules
<IfModule mod_rewrite.c>

RewriteEngine on

# Make sure to set the RewriteBase correctly
# if you are running the site in a subfolder;
# otherwise links or the entire site will break.
#
# If your homepage is https://yourdomain.com/mysite,
# set the RewriteBase to:
#
# RewriteBase /mysite

# In some environments it's necessary to
# set the RewriteBase to:
#
# RewriteBase /

# Block files and folders beginning with a dot, such as .git
# except for the .well-known folder, which is used for Let's Encrypt and security.txt
RewriteRule (^|/)\.(?!well-known\/) index.php [L]

# Block all files in the content folder from being accessed directly
RewriteRule ^content/(.*) index.php [L]

# Block all files in the site folder from being accessed directly
RewriteRule ^site/(.*) index.php [L]

# Block all files in the kirby folder from being accessed directly
RewriteRule ^kirby/(.*) index.php [L]

# Make site links work
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*) index.php [L]

</IfModule>

# Additional recommended mime types
AddType image/svg+xml svg svgz
AddEncoding gzip svgz
"""

        with open(htaccess_path, 'w') as f:
            f.write(htaccess_content)

        self.log("Created .htaccess file")

    def get_installation_info(self, kirby_path: str) -> Dict[str, Any]:
        """Get information about the Kirby installation"""
        if not self._is_kirby_installation(kirby_path):
            return {'installed': False}

        return {
            'installed': True,
            'path': kirby_path,
            'site_path': os.path.join(kirby_path, 'site'),
            'content_path': os.path.join(kirby_path, 'content'),
            'blueprints_path': os.path.join(kirby_path, 'site', 'blueprints'),
            'templates_path': os.path.join(kirby_path, 'site', 'templates'),
        }
