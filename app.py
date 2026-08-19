from flask import Flask, jsonify, render_template
from flask import send_from_directory
from pathlib import Path
import mysql.connector
from mysql.connector import Error

app = Flask(__name__, template_folder=".frontend", static_folder=".frontend")

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / ".frontend"


def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            port=3306,
            user="root",
            password="",
            database="smart_study",
            autocommit=True,
        )
        return conn
    except Error as exc:
        print(f"MySQL connection error: {exc}")
        return None


def init_db():
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE DATABASE IF NOT EXISTS smart_study
        """)
        cursor.execute("USE smart_study")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dashboard_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                section VARCHAR(50) NOT NULL,
                payload JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("SELECT COUNT(*) FROM dashboard_data")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO dashboard_data (section, payload) VALUES
                ('user', '{"name":"Jones"}'),
                ('categories', '[{"icon":"🎨","name":"Graphic Design","watched":8,"total":15},{"icon":"💻","name":"Coding","watched":2,"total":9},{"icon":"📈","name":"Marketing","watched":2,"total":9}]'),
                ('courses', '[{"category":"Coding","title":"Kursus Tiga","author":"John Doe","duration":"3 jam • Menengah","progress":55},{"category":"Coding","title":"Kursus Dua","author":"Michael Brown","duration":"2 jam • Pemula","progress":30},{"category":"Graphic Design","title":"Kursus Empat","author":"James Smith","duration":"3 jam • Ahli","progress":80}]'),
                ('progress', '{"completed":60,"inProgress":40,"notStarted":20}'),
                ('tasks', '[{"icon":"📌","title":"Mulai Tugas Satu","remaining":"3 hari 16 jam tersisa"},{"icon":"✏️","title":"Mulai Tugas Dua","remaining":"3 hari 20 jam tersisa"},{"icon":"📐","title":"Mulai Tugas Tiga","remaining":"4 hari 6 jam tersisa"}]')
            """)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error as exc:
        print(f"DB init error: {exc}")
        return False


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/api/dashboard")
def dashboard_api():
    conn = get_db_connection()
    if conn is None:
        return jsonify({
            "user": {"name": "Jones"},
            "categories": [
                {"icon": "🎨", "name": "Graphic Design", "watched": 8, "total": 15},
                {"icon": "💻", "name": "Coding", "watched": 2, "total": 9},
                {"icon": "📈", "name": "Marketing", "watched": 2, "total": 9},
            ],
            "courses": [
                {"category": "Coding", "title": "Kursus Tiga", "author": "John Doe", "duration": "3 jam • Menengah", "progress": 55},
                {"category": "Coding", "title": "Kursus Dua", "author": "Michael Brown", "duration": "2 jam • Pemula", "progress": 30},
                {"category": "Graphic Design", "title": "Kursus Empat", "author": "James Smith", "duration": "3 jam • Ahli", "progress": 80},
            ],
            "progress": {"completed": 60, "inProgress": 40, "notStarted": 20},
            "tasks": [
                {"icon": "📌", "title": "Mulai Tugas Satu", "remaining": "3 hari 16 jam tersisa"},
                {"icon": "✏️", "title": "Mulai Tugas Dua", "remaining": "3 hari 20 jam tersisa"},
                {"icon": "📐", "title": "Mulai Tugas Tiga", "remaining": "4 hari 6 jam tersisa"},
            ],
        })

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("USE smart_study")
        cursor.execute("SELECT section, payload FROM dashboard_data")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        data = {}
        for row in rows:
            if row["section"] == "user":
                data["user"] = row["payload"] if isinstance(row["payload"], dict) else {"name": "Jones"}
            elif row["section"] == "progress":
                data["progress"] = row["payload"]
            else:
                data[row["section"]] = row["payload"]

        if not data:
            raise ValueError("No data found")
        return jsonify(data)
    except Exception as exc:
        print(f"Dashboard API error: {exc}")
        return jsonify({"error": str(exc)}), 500


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
