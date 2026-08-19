"""
server.py — Backend Python untuk MyCourse Dashboard
Menyajikan file statis (index.html, style.css, script.js)
dan endpoint API JSON (/api/dashboard) sebagai sumber data.

Cara jalankan:
    python server.py
Lalu buka browser ke:
    http://localhost:8000
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PORT = 8000
BASE_DIR = Path(__file__).parent


# ==================== "DATABASE" SEDERHANA ====================
def get_dashboard_data():
    return {
        "user": {"name": "Jones"},
        "categories": [
            {"icon": "🎨", "name": "Graphic Design", "watched": 8, "total": 15},
            {"icon": "💻", "name": "Coding", "watched": 2, "total": 9},
            {"icon": "📈", "name": "Marketing", "watched": 2, "total": 9},
        ],
        "courses": [
            {"category": "Coding", "title": "Kursus Tiga", "author": "John Doe",
             "duration": "3 jam • Menengah", "progress": 55},
            {"category": "Coding", "title": "Kursus Dua", "author": "Michael Brown",
             "duration": "2 jam • Pemula", "progress": 30},
            {"category": "Graphic Design", "title": "Kursus Empat", "author": "James Smith",
             "duration": "3 jam • Ahli", "progress": 80},
        ],
        "progress": {"completed": 60, "inProgress": 40, "notStarted": 20},
        "tasks": [
            {"icon": "📌", "title": "Mulai Tugas Satu", "remaining": "3 hari 16 jam tersisa"},
            {"icon": "✏️", "title": "Mulai Tugas Dua", "remaining": "3 hari 20 jam tersisa"},
            {"icon": "📐", "title": "Mulai Tugas Tiga", "remaining": "4 hari 6 jam tersisa"},
        ],
    }


# ==================== HTTP HANDLER ====================
MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/dashboard":
            self._send_json(get_dashboard_data())
            return

        # Static file serving
        route = "/index.html" if self.path == "/" else self.path
        file_path = BASE_DIR / route.lstrip("/")

        if file_path.exists() and file_path.is_file():
            content_type = MIME_TYPES.get(file_path.suffix, "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(file_path.read_bytes())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def _send_json(self, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[server] {self.address_string()} - {format % args}")


if __name__ == "__main__":
    server = HTTPServer(("localhost", PORT), DashboardHandler)
    print(f"✅ Server jalan di http://localhost:{PORT}")
    print("Tekan CTRL+C untuk berhenti.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
