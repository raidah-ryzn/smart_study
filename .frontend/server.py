"""
server.py — Backend Python untuk MyCourse Dashboard
Menyajikan file statis (index.html, login.html, signup.html, style.css, script.js)
dan endpoint API JSON (/api/dashboard, /api/register, /api/login, /api/logout,
/api/auth/status) untuk autentikasi + data dashboard.

Data user disimpan di file users.json (dibuat otomatis) dengan password ter-hash
(PBKDF2-SHA256 + salt) — bukan plaintext.

Cara jalankan:
    python server.py
Lalu buka browser ke:
    http://localhost:8000
"""

import hashlib
import hmac
import json
import os
import re
import secrets
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

PORT = 8000
BASE_DIR = Path(__file__).parent
USERS_FILE = BASE_DIR / "users.json"

# Kode rahasia harus sama dengan server utama (hallo.py).
ADMIN_SECRET_CODE = os.getenv("ADMIN_CODE", "SMART-STUDY-ADMIN")

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


# ==================== PENYIMPANAN USER (file JSON) ====================
def load_users():
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_users(users):
    USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False), encoding="utf-8")


users_db = load_users()   # key: email (lowercase) -> {name, email, password_hash, account_role}
sessions = {}             # key: session token -> email


def hash_password(password: str, salt: bytes = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex() + ":" + dk.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split(":")
    except (ValueError, AttributeError):
        return False
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return hmac.compare_digest(dk.hex(), hash_hex)


# ==================== "DATABASE" DASHBOARD (contoh statis) ====================
def get_dashboard_data(user):
    return {
        "user": {"name": user.get("name", "User")},
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
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
}


class DashboardHandler(BaseHTTPRequestHandler):

    # ---------- helpers ----------
    def _read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _send_json(self, data, status=200, extra_headers=None):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _get_session_token(self):
        cookie_header = self.headers.get("Cookie")
        if not cookie_header:
            return None
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        morsel = cookie.get("session_token")
        return morsel.value if morsel else None

    def _get_session_user(self):
        token = self._get_session_token()
        if not token:
            return None
        email = sessions.get(token)
        if not email:
            return None
        return users_db.get(email)

    # ---------- GET ----------
    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/dashboard":
            user = self._get_session_user()
            if not user:
                self._send_json({"message": "Belum login"}, status=401)
                return
            self._send_json(get_dashboard_data(user))
            return

        if path == "/api/auth/status":
            user = self._get_session_user()
            if user:
                self._send_json({
                    "authenticated": True,
                    "user_id": user["email"],
                    "role": user["account_role"],
                })
            else:
                self._send_json({"authenticated": False})
            return

        # Static file serving — map clean URLs (tanpa .html) ke file HTML-nya
        ROUTE_ALIASES = {
            "/": "/index.html",
            "/login": "/login.html",
            "/signup": "/signup.html",
            "/dashboard": "/index.html",
        }
        route = ROUTE_ALIASES.get(path, path)
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

    # ---------- POST ----------
    def do_POST(self):
        path = urlparse(self.path).path
        data = self._read_json_body()

        if path == "/api/register":
            self._handle_register(data)
            return

        if path == "/api/login":
            self._handle_login(data)
            return

        if path == "/api/logout":
            self._handle_logout()
            return

        self._send_json({"message": "Endpoint tidak ditemukan"}, status=404)

    # ---------- auth handlers ----------
    def _handle_register(self, data):
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        password_confirm = data.get("password_confirm") or ""
        account_role = (data.get("account_role") or "user").strip().lower()
        admin_code = (data.get("admin_code") or "").strip()

        if not name or not email or not password:
            self._send_json({"message": "Nama, email, dan password wajib diisi"}, status=400)
            return

        if not EMAIL_RE.match(email):
            self._send_json({"message": "Email tidak valid"}, status=400)
            return

        if len(password) < 6:
            self._send_json({"message": "Password minimal 6 karakter"}, status=400)
            return

        if password != password_confirm:
            self._send_json({"message": "Konfirmasi password tidak cocok"}, status=400)
            return

        if account_role == "admin" and admin_code != ADMIN_SECRET_CODE:
            self._send_json({"message": "Kode admin salah"}, status=400)
            return

        if email in users_db:
            self._send_json({"message": "Email sudah terdaftar"}, status=409)
            return

        users_db[email] = {
            "name": name,
            "email": email,
            "password_hash": hash_password(password),
            "account_role": "admin" if account_role == "admin" else "user",
        }
        save_users(users_db)

        self._send_json({"message": "Registrasi berhasil! Silakan login."}, status=201)

    def _handle_login(self, data):
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        account_role = (data.get("account_role") or "user").strip().lower()
        admin_code = (data.get("admin_code") or "").strip()

        user = users_db.get(email)

        if not user or not verify_password(password, user.get("password_hash", "")):
            self._send_json({"message": "Email atau password salah"}, status=401)
            return

        if account_role == "admin":
            if user["account_role"] != "admin":
                self._send_json({"message": "Akun ini tidak terdaftar sebagai admin"}, status=403)
                return
            if admin_code != ADMIN_SECRET_CODE:
                self._send_json({"message": "Kode admin salah"}, status=403)
                return

        token = secrets.token_hex(24)
        sessions[token] = email

        self._send_json(
            {"message": "Login berhasil", "role": user["account_role"]},
            extra_headers={"Set-Cookie": f"session_token={token}; Path=/; HttpOnly"},
        )

    def _handle_logout(self):
        token = self._get_session_token()
        if token and token in sessions:
            del sessions[token]
        self._send_json(
            {"message": "Logout berhasil"},
            extra_headers={"Set-Cookie": "session_token=; Path=/; Max-Age=0"},
        )

    def log_message(self, format, *args):
        print(f"[server] {self.address_string()} - {format % args}")


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), DashboardHandler)
    print(f"✅ Server jalan di http://localhost:{PORT}")
    print(f"   Akses perangkat lain: http://IP-KOMPUTER:{PORT}")
    print(f"   Kode admin untuk daftar/login sebagai Admin: {ADMIN_SECRET_CODE}")
    print("Tekan CTRL+C untuk berhenti.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer dihentikan.")
