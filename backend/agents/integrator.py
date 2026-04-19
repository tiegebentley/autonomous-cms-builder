"""
Integrator Agent - Integrates generated CMS files into Kirby and starts server

This agent:
1. Merges generated blueprints/templates into Kirby
2. Handles conflicts (existing files)
3. Starts PHP development server
4. Tests that CMS is accessible
5. Returns access URLs
"""
import os
import shutil
import subprocess
import time
import signal
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from .base import BaseAgent


class IntegratorAgent:
    """Agent responsible for integrating CMS files and starting server (standalone, not inheriting BaseAgent)"""

    def __init__(self):
        self.name = "integrator"
        self.icon = "🔗"
        self.logs = []
        self.running_servers = {}  # Track running PHP servers

    def log(self, message: str, level: str = "info"):
        """Log a message"""
        self.logs.append({"message": message, "level": level})
        print(f"[{self.name}] {message}")

    async def execute(
        self,
        kirby_path: str,
        generated_files_path: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Integrate generated files into Kirby and start server

        Args:
            kirby_path: Path to Kirby installation
            generated_files_path: Path to generated CMS files
            options: Integration options
                - port: int - PHP server port (default: 8080)
                - merge_strategy: str - 'overwrite' or 'skip' (default: overwrite)
                - auto_start: bool - Start server automatically (default: True)

        Returns:
            Integration result with URLs and server info
        """
        try:
            self.log("Starting CMS integration...")

            # Merge files into Kirby
            merge_result = await self._merge_files(kirby_path, generated_files_path, options)
            self.log(f"✅ Merged {merge_result['files_copied']} files")

            # Start PHP server if requested
            server_info = None
            if options.get('auto_start', True):
                port = options.get('port', 8080)
                server_info = await self._start_server(kirby_path, port)
                self.log(f"✅ Server started on port {port}")

                # Test accessibility
                test_result = await self._test_server(server_info['url'])
                if test_result['accessible']:
                    self.log("✅ CMS is accessible and working!")
                else:
                    self.log("⚠️ Server started but CMS may not be fully accessible", level="warning")

            return {
                'success': True,
                'kirby_path': kirby_path,
                'merge_result': merge_result,
                'server_info': server_info,
                'urls': {
                    'cms': server_info['url'] if server_info else None,
                    'panel': f"{server_info['url']}/panel" if server_info else None,
                },
                'message': 'CMS integrated and server started successfully'
            }

        except Exception as e:
            self.log(f"❌ Integration failed: {str(e)}", level="error")
            raise Exception(f"CMS integration failed: {str(e)}")

    async def _merge_files(
        self,
        kirby_path: str,
        generated_path: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Merge generated CMS files into Kirby installation

        Handles:
        - Blueprints (site/blueprints/)
        - Templates (site/templates/)
        - Content (content/)
        """
        merge_strategy = options.get('merge_strategy', 'overwrite') if options else 'overwrite'
        files_copied = 0
        files_skipped = 0
        conflicts = []

        self.log(f"Merging files with strategy: {merge_strategy}")

        # Define source -> destination mappings
        mappings = [
            (
                os.path.join(generated_path, 'site', 'blueprints'),
                os.path.join(kirby_path, 'site', 'blueprints')
            ),
            (
                os.path.join(generated_path, 'site', 'templates'),
                os.path.join(kirby_path, 'site', 'templates')
            ),
            (
                os.path.join(generated_path, 'site', 'snippets'),
                os.path.join(kirby_path, 'site', 'snippets')
            ),
            (
                os.path.join(generated_path, 'content'),
                os.path.join(kirby_path, 'content')
            ),
        ]

        for source_dir, dest_dir in mappings:
            if not os.path.exists(source_dir):
                continue

            # Create destination directory if it doesn't exist
            os.makedirs(dest_dir, exist_ok=True)

            # Copy files
            for root, dirs, files in os.walk(source_dir):
                # Calculate relative path
                rel_path = os.path.relpath(root, source_dir)
                dest_root = os.path.join(dest_dir, rel_path) if rel_path != '.' else dest_dir

                # Create subdirectories
                os.makedirs(dest_root, exist_ok=True)

                # Copy files
                for file in files:
                    source_file = os.path.join(root, file)
                    dest_file = os.path.join(dest_root, file)

                    # Check for conflicts
                    if os.path.exists(dest_file):
                        conflicts.append(dest_file)
                        if merge_strategy == 'skip':
                            self.log(f"⏭️  Skipping existing file: {file}")
                            files_skipped += 1
                            continue

                    # Copy file
                    shutil.copy2(source_file, dest_file)
                    files_copied += 1
                    self.log(f"📄 Copied: {file}")

        return {
            'files_copied': files_copied,
            'files_skipped': files_skipped,
            'conflicts': conflicts,
            'merge_strategy': merge_strategy
        }

    async def _start_server(self, kirby_path: str, port: int = 8080) -> Dict[str, Any]:
        """
        Start PHP development server for Kirby

        Args:
            kirby_path: Path to Kirby installation
            port: Port to run server on

        Returns:
            Server information
        """
        # Check if port is already in use
        if self._is_port_in_use(port):
            self.log(f"⚠️ Port {port} already in use, attempting to kill existing process...")
            self._kill_process_on_port(port)
            time.sleep(2)  # Wait for port to be released

        # Start PHP server with Kirby router in background
        server_process = subprocess.Popen(
            ['php', '-S', f'localhost:{port}', '-t', '.', 'kirby/router.php'],
            cwd=kirby_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid  # Create new process group
        )

        # Wait a moment for server to start
        time.sleep(3)

        # Check if server is running
        if server_process.poll() is not None:
            # Process died
            stdout, stderr = server_process.communicate()
            raise Exception(f"Failed to start PHP server: {stderr.decode()}")

        # Store server info
        server_id = f"{kirby_path}:{port}"
        self.running_servers[server_id] = {
            'process': server_process,
            'pid': server_process.pid,
            'port': port,
            'path': kirby_path,
            'started_at': datetime.now().isoformat()
        }

        return {
            'pid': server_process.pid,
            'port': port,
            'url': f'http://localhost:{port}',
            'panel_url': f'http://localhost:{port}/panel',
            'server_id': server_id
        }

    async def _test_server(self, url: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Test if the server is accessible

        Args:
            url: URL to test
            max_retries: Number of retry attempts

        Returns:
            Test results
        """
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    return {
                        'accessible': True,
                        'status_code': response.status_code,
                        'url': url
                    }
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    self.log(f"Retry {attempt + 1}/{max_retries} - Server not ready yet...")
                    time.sleep(2)
                else:
                    return {
                        'accessible': False,
                        'error': str(e),
                        'url': url
                    }

        return {'accessible': False, 'url': url}

    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is already in use"""
        result = subprocess.run(
            ['lsof', '-i', f':{port}'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0

    def _kill_process_on_port(self, port: int):
        """Kill process using specified port"""
        try:
            subprocess.run(
                ['lsof', '-ti', f':{port}', '|', 'xargs', 'kill', '-9'],
                shell=True,
                check=False
            )
        except Exception as e:
            self.log(f"Could not kill process on port {port}: {e}", level="warning")

    def stop_server(self, server_id: str) -> bool:
        """Stop a running PHP server"""
        if server_id not in self.running_servers:
            return False

        server_info = self.running_servers[server_id]
        try:
            # Kill process group
            os.killpg(os.getpgid(server_info['pid']), signal.SIGTERM)
            self.log(f"✅ Stopped server on port {server_info['port']}")
            del self.running_servers[server_id]
            return True
        except Exception as e:
            self.log(f"Failed to stop server: {str(e)}", level="error")
            return False

    def get_running_servers(self) -> List[Dict[str, Any]]:
        """Get list of all running servers"""
        return [
            {
                'server_id': server_id,
                **info
            }
            for server_id, info in self.running_servers.items()
        ]

    def stop_all_servers(self):
        """Stop all running servers"""
        for server_id in list(self.running_servers.keys()):
            self.stop_server(server_id)
