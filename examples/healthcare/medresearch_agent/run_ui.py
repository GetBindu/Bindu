"""
Simple HTTP Server for MedResearch Agent UI

This serves the web interface for the agent.
Run this alongside the agent to access the UI.
"""

import http.server
import socketserver
import webbrowser
from pathlib import Path

PORT = 8081
DIRECTORY = Path(__file__).parent / "ui"


class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP Request Handler with CORS support."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def end_headers(self):
        """Add CORS headers to allow cross-origin requests."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        """Handle preflight OPTIONS requests."""
        self.send_response(200)
        self.end_headers()


def main():
    """Start the web server."""
    print("=" * 60)
    print("🏥 MedResearch Agent - Web UI Server")
    print("=" * 60)
    print()

    # Check if UI directory exists
    if not DIRECTORY.exists():
        print(f"❌ Error: UI directory not found at {DIRECTORY}")
        print("   Make sure the 'ui' folder with index.html exists.")
        return

    # Start server
    with socketserver.TCPServer(("", PORT), CORSHTTPRequestHandler) as httpd:
        url = f"http://localhost:{PORT}"

        print(f"✅ UI Server started successfully!")
        print()
        print(f"🌐 Open in browser: {url}")
        print()
        print("📝 Instructions:")
        print("   1. Make sure the agent is running (python medresearch_agent.py)")
        print("   2. Agent should be at http://localhost:3773")
        print("   3. Open the UI in your browser")
        print("   4. Upload papers and start analyzing!")
        print()
        print("Press Ctrl+C to stop the server")
        print()

        # Try to open browser automatically
        try:
            print("🚀 Opening browser...")
            webbrowser.open(url)
        except Exception as e:
            print(f"⚠️  Could not open browser automatically: {e}")
            print(f"   Please open {url} manually")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped. Goodbye!")


if __name__ == "__main__":
    main()
