#!/usr/bin/env python3
"""
DV Wizard Server
Serves the GUI and provides an API to execute generation scripts.
"""
import os
import sys
import json
import subprocess
import http.server
import socketserver
from urllib.parse import urlparse

SCRIPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')

# Map TB type to script filename
SCRIPT_MAP = {
    'IP':  'generate_ip.py',
    'SS':  'generate_ss.py',
    'SoC': 'generate_soc.py',
    'VIP': 'generate_vip.py',
}


class DVWizardHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler that adds POST /api/execute endpoint."""

    CONFIG_FILENAME = 'proj.config'

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == '/api/execute':
            self._handle_execute()
        elif parsed.path == '/api/load-project':
            self._handle_load_project()
        elif parsed.path == '/api/save-project':
            self._handle_save_project()
        elif parsed.path == '/api/scan-directory':
            self._handle_scan_directory()
        else:
            self.send_error(404, 'Not Found')

    def _handle_load_project(self):
        """Check if proj.config exists in the given TB root directory and return its contents."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body)
            tb_root = payload.get('tb_root', '')

            if not tb_root or not os.path.isdir(tb_root):
                self._json_response(200, {'found': False, 'reason': 'Directory does not exist'})
                return

            config_path = os.path.join(tb_root, self.CONFIG_FILENAME)
            if not os.path.isfile(config_path):
                self._json_response(200, {'found': False, 'reason': 'No proj.config found'})
                return

            with open(config_path, 'r') as f:
                config = json.load(f)

            self._json_response(200, {'found': True, 'config': config, 'path': config_path})

        except json.JSONDecodeError:
            self._json_response(400, {'error': 'Invalid JSON in request or proj.config'})
        except Exception as e:
            self._json_response(500, {'error': str(e)})

    def _handle_save_project(self):
        """Save the wizard config as proj.config in the TB root directory."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body)

            tb_root = payload.get('tb_root', '')
            config = payload.get('config', {})

            if not tb_root:
                self._json_response(400, {'error': 'tb_root is required'})
                return

            # Create directory if it doesn't exist
            os.makedirs(tb_root, exist_ok=True)

            config_path = os.path.join(tb_root, self.CONFIG_FILENAME)
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            self._json_response(200, {'success': True, 'path': config_path})

        except json.JSONDecodeError:
            self._json_response(400, {'error': 'Invalid JSON'})
        except PermissionError:
            self._json_response(500, {'error': f'Permission denied writing to {tb_root}'})
        except Exception as e:
            self._json_response(500, {'error': str(e)})

    def _handle_scan_directory(self):
        """Scan TB root directory for IPs, VIPs, and SSes based on naming conventions.

        Naming rules:
          - IP directories contain '_ip' in their name (e.g., pcie_ip, dma_ip, usb_ip)
          - VIP directories contain '_vip' in their name (e.g., axi_vip, apb_vip)
          - SS directories contain '_ss' in their name (e.g., pcie_ss, dma_ss)
        Directories not following these conventions are flagged with warnings.
        """
        import re

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body)

            scan_path = payload.get('path', '')
            scan_depth = payload.get('depth', 2)  # how many levels deep to scan

            if not scan_path or not os.path.isdir(scan_path):
                self._json_response(200, {'found': False, 'reason': 'Directory does not exist'})
                return

            ips = []
            vips = []
            sses = []
            warnings = []

            def classify_dir(dirpath, dirname, depth):
                """Classify a directory based on naming convention."""
                name_lower = dirname.lower()
                rel_path = os.path.relpath(dirpath, scan_path)
                has_ip = '_ip' in name_lower
                has_vip = '_vip' in name_lower
                has_ss = '_ss' in name_lower

                # Count how many conventions match
                matches = sum([has_ip, has_vip, has_ss])

                if matches == 0:
                    # Skip common known directories
                    skip_names = {'dv', 'rtl', 'env', 'tb', 'tests', 'sequences', 'docs',
                                  'common', 'scripts', 'firmware', '.git', '.claude',
                                  'src', 'soc_top', 'test_project', '__pycache__'}
                    if dirname.lower() not in skip_names and not dirname.startswith('.'):
                        warnings.append({
                            'path': rel_path,
                            'name': dirname,
                            'message': f"'{dirname}' does not follow naming convention (_ip, _vip, or _ss). Cannot auto-classify."
                        })
                    return

                if matches > 1:
                    warnings.append({
                        'path': rel_path,
                        'name': dirname,
                        'message': f"'{dirname}' matches multiple conventions. Ambiguous classification."
                    })

                # Scan for sub-VIPs inside this directory
                sub_vips = []
                if os.path.isdir(dirpath):
                    for sub in sorted(os.listdir(dirpath)):
                        sub_full = os.path.join(dirpath, sub)
                        if os.path.isdir(sub_full) and '_vip' in sub.lower():
                            sub_vips.append({'name': sub, 'path': os.path.relpath(sub_full, scan_path)})
                        # Also check inside dv/ subdirectory
                    dv_dir = os.path.join(dirpath, 'dv')
                    if os.path.isdir(dv_dir):
                        for sub in sorted(os.listdir(dv_dir)):
                            sub_full = os.path.join(dv_dir, sub)
                            if os.path.isdir(sub_full) and '_vip' in sub.lower():
                                sub_vips.append({'name': sub, 'path': os.path.relpath(sub_full, scan_path)})

                entry = {
                    'name': dirname,
                    'path': rel_path,
                    'full_path': dirpath,
                    'vips': sub_vips,
                }

                if has_vip and not has_ip and not has_ss:
                    vips.append(entry)
                elif has_ip and not has_vip:
                    ips.append(entry)
                elif has_ss:
                    # For SS, also scan for sub-IPs
                    sub_ips = []
                    for sub in sorted(os.listdir(dirpath)):
                        sub_full = os.path.join(dirpath, sub)
                        if os.path.isdir(sub_full) and '_ip' in sub.lower():
                            # Get VIPs inside this sub-IP
                            ip_vips = []
                            for vdir in sorted(os.listdir(sub_full)):
                                vfull = os.path.join(sub_full, vdir)
                                if os.path.isdir(vfull) and '_vip' in vdir.lower():
                                    ip_vips.append({'name': vdir, 'path': os.path.relpath(vfull, scan_path)})
                            dv_sub = os.path.join(sub_full, 'dv')
                            if os.path.isdir(dv_sub):
                                for vdir in sorted(os.listdir(dv_sub)):
                                    vfull = os.path.join(dv_sub, vdir)
                                    if os.path.isdir(vfull) and '_vip' in vdir.lower():
                                        ip_vips.append({'name': vdir, 'path': os.path.relpath(vfull, scan_path)})
                            sub_ips.append({
                                'name': sub,
                                'path': os.path.relpath(sub_full, scan_path),
                                'vips': ip_vips,
                            })
                    entry['ips'] = sub_ips
                    sses.append(entry)

            # Scan top-level directories
            for item in sorted(os.listdir(scan_path)):
                item_path = os.path.join(scan_path, item)
                if not os.path.isdir(item_path) or item.startswith('.'):
                    continue
                classify_dir(item_path, item, 0)

                # Scan one level deeper for IPs inside SSes (already handled in classify_dir for _ss)
                # Also scan 'common' directory for VIPs
                if item.lower() == 'common':
                    for sub in sorted(os.listdir(item_path)):
                        sub_path = os.path.join(item_path, sub)
                        if os.path.isdir(sub_path):
                            classify_dir(sub_path, sub, 1)

            self._json_response(200, {
                'found': True,
                'ips': ips,
                'vips': vips,
                'sses': sses,
                'warnings': warnings,
                'scanned_path': scan_path,
            })

        except json.JSONDecodeError:
            self._json_response(400, {'error': 'Invalid JSON'})
        except PermissionError:
            self._json_response(500, {'error': f'Permission denied reading directory'})
        except Exception as e:
            self._json_response(500, {'error': str(e)})

    def _handle_execute(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body)

            tb_type = payload.get('tb_type', 'IP')
            script_name = SCRIPT_MAP.get(tb_type)

            if not script_name:
                self._json_response(400, {'error': f'Unknown tb_type: {tb_type}'})
                return

            script_path = os.path.join(SCRIPT_DIR, script_name)
            if not os.path.exists(script_path):
                self._json_response(500, {'error': f'Script not found: {script_name}'})
                return

            # Execute the script, passing config JSON via stdin
            config_json = json.dumps(payload)
            result = subprocess.run(
                [sys.executable, script_path],
                input=config_json,
                capture_output=True,
                text=True,
                timeout=120,
            )

            output_lines = []
            if result.stdout:
                output_lines = [line for line in result.stdout.split('\n') if line.strip()]
            if result.stderr:
                for line in result.stderr.split('\n'):
                    if line.strip():
                        output_lines.append(f'[stderr] {line}')

            self._json_response(200, {
                'success': result.returncode == 0,
                'return_code': result.returncode,
                'lines': output_lines,
                'script': script_name,
            })

        except json.JSONDecodeError:
            self._json_response(400, {'error': 'Invalid JSON'})
        except subprocess.TimeoutExpired:
            self._json_response(500, {'error': 'Script timed out (120s)'})
        except Exception as e:
            self._json_response(500, {'error': str(e)})

    def _json_response(self, code, data):
        body = json.dumps(data).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, fmt, *args):
        # Quieter logging — only show API calls
        if '/api/' in (args[0] if args else ''):
            super().log_message(fmt, *args)


os.chdir(os.path.dirname(os.path.abspath(__file__)))
port = int(os.environ.get('PORT', 8765))

with socketserver.TCPServer(("", port), DVWizardHandler) as httpd:
    print(f"DV-Wizard serving at http://localhost:{port}")
    print(f"Scripts directory: {SCRIPT_DIR}")
    print(f"Available scripts: {list(SCRIPT_MAP.values())}")
    httpd.serve_forever()
