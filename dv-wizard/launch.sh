#!/bin/bash
# DV Wizard - Launch Script
# Works on Linux/Unix/macOS with Python 3
#
# Usage:
#   ./launch.sh              # Opens on port 8765
#   ./launch.sh 9000         # Opens on custom port
#   ./launch.sh --no-open    # Start server without opening browser

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-8765}"
NO_OPEN=false

if [ "$1" = "--no-open" ]; then
    NO_OPEN=true
    PORT="${2:-8765}"
elif [ "$2" = "--no-open" ]; then
    NO_OPEN=true
fi

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3."
    exit 1
fi

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║        DV Wizard - Starting...       ║"
echo "  ║   Design Verification Suite          ║"
echo "  ╚══════════════════════════════════════╝"
echo ""
echo "  Server: http://localhost:${PORT}"
echo "  Directory: ${SCRIPT_DIR}"
echo "  Press Ctrl+C to stop"
echo ""

# Try to open browser (skip on headless/SSH)
if [ "$NO_OPEN" = false ]; then
    if [ -n "$DISPLAY" ] || [ "$(uname)" = "Darwin" ]; then
        sleep 1 &
        (sleep 1 && {
            if command -v xdg-open &> /dev/null; then
                xdg-open "http://localhost:${PORT}/index.html" 2>/dev/null
            elif command -v open &> /dev/null; then
                open "http://localhost:${PORT}/index.html" 2>/dev/null
            elif command -v firefox &> /dev/null; then
                firefox "http://localhost:${PORT}/index.html" 2>/dev/null &
            fi
        }) &
    else
        echo "  (No display detected - open http://localhost:${PORT}/index.html in your browser)"
        echo ""
    fi
fi

# Start server
cd "$SCRIPT_DIR"
python3 -c "
import http.server, socketserver, os
os.chdir('${SCRIPT_DIR}')
handler = http.server.SimpleHTTPRequestHandler
handler.extensions_map.update({'.js': 'application/javascript', '.css': 'text/css'})
with socketserver.TCPServer(('', ${PORT}), handler) as httpd:
    httpd.serve_forever()
"
