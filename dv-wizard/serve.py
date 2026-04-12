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
