#!/usr/bin/env python3
import os, http.server, socketserver
os.chdir(os.path.dirname(os.path.abspath(__file__)))
port = int(os.environ.get('PORT', 8765))
handler = http.server.SimpleHTTPRequestHandler
with socketserver.TCPServer(("", port), handler) as httpd:
    print(f"Serving DV-Wizard at http://localhost:{port}")
    httpd.serve_forever()
