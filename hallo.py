import json
import os
import hashlib
import base64
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps

import mysql.connector
from flask import Flask, jsonify, send_from_directory, request, session, redirect
from mysql.connector import Error
from werkzeug.utils import secure_filename

app = Flask(__name__, template_folder='.frontend', static_folder='.frontend')
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
ADMIN_CODE = os.getenv('ADMIN_CODE', 'SMART-STUDY-ADMIN')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / '.frontend'
UPLOAD_DIR = BASE_DIR / 'uploads' / 'assignments'


def get_default_dashboard():
    return {
        'user': {'name': 'Jones'},
        'categories': [
            {'icon': '🎨', 'name': 'Graphic Design', 'watched': 8, 'total': 15},
            {'icon': '💻', 'name': 'Coding', 'watched': 2, 'total': 9},
            {'icon': '📈', 'name': 'Marketing', 'watched': 2, 'total': 9},
        ],
        'courses': [
            {'category': 'Coding', 'title': 'Kursus Tiga', 'author': 'John Doe', 'duration': '3 jam • Menengah', 'progress': 55},
            {'category': 'Coding', 'title': 'Kursus Dua', 'author': 'Michael Brown', 'duration': '2 jam • Pemula', 'progress': 30},
            {'category': 'Graphic Design', 'title': 'Kursus Empat', 'author': 'James Smith', 'duration': '3 jam • Ahli', 'progress': 80},
        ],
        'progress': {'completed': 60, 'inProgress': 40, 'notStarted': 20},
        'tasks': [
            {'icon': '📌', 'title': 'Mulai Tugas Satu', 'remaining': '3 hari 16 jam tersisa'},
            {'icon': '✏️', 'title': 'Mulai Tugas Dua', 'remaining': '3 hari 20 jam tersisa'},
            {'icon': '📐', 'title': 'Mulai Tugas Tiga', 'remaining': '4 hari 6 jam tersisa'},
        ],
    }


def get_db_connection(database=None):
    try:
        config = {
            'host': os.getenv('DB_HOST', '127.0.0.1'),
            'port': int(os.getenv('DB_PORT', '3306')),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'autocommit': True,
        }
        target_db = database or os.getenv('DB_NAME')
        if target_db:
            config['database'] = target_db
        return mysql.connector.connect(**config)
    except Error as exc:
        print(f'MySQL connection error: {exc}')
        return None


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'message': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'message': 'Unauthorized'}), 401

        user = get_user_by_id(session['user_id'])
        if not user or str(user.get('role', 'user')).lower() != 'admin':
            return jsonify({'message': 'Forbidden'}), 403
        return f(*args, **kwargs)
    return decorated_function


def get_user_by_id(user_id):
    conn = get_db_connection('smart_study')
    if not conn:
        return None

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        cursor.close(); conn.close(); return user
    except Exception as exc:
        print(f'Get user by id error: {exc}')
        return None


def get_user_by_email(email):
    conn = get_db_connection('smart_study')
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    except Exception as exc:
        print(f'Get user error: {exc}')
        return None


def create_user(email, name, password_hash=None, google_id=None, profile_picture=None,
                role='user', verification_code=None, is_verified=0):
    conn = get_db_connection('smart_study')
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (email, name, password_hash, google_id, profile_picture, role, verification_code, is_verified)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (email, name, password_hash, google_id, profile_picture,
                            role, verification_code, is_verified))
        user_id = cursor.lastrowid
        
        cursor.execute('UPDATE users SET last_login = NOW() WHERE id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return user_id
    except Exception as exc:
        print(f'Create user error: {exc}')
        return None


def update_last_login(user_id):
    conn = get_db_connection('smart_study')
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_login = NOW() WHERE id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as exc:
        print(f'Update last login error: {exc}')
        return False


def create_notification(user_id, title, message, notification_type='general'):
    if not user_id:
        return None

    conn = get_db_connection('smart_study')
    if not conn:
        return None

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT notifications_assignments, notifications_messages, notifications_events FROM user_settings WHERE user_id = %s', (user_id,))
        settings = cursor.fetchone()

        if notification_type == 'tugas' and settings is not None and int(settings.get('notifications_assignments', 1)) == 0:
            cursor.close(); conn.close(); return None
        if notification_type == 'pesan' and settings is not None and int(settings.get('notifications_messages', 1)) == 0:
            cursor.close(); conn.close(); return None
        if notification_type == 'event' and settings is not None and int(settings.get('notifications_events', 1)) == 0:
            cursor.close(); conn.close(); return None

        cursor.execute('''
            INSERT INTO notifications (user_id, title, message, type, is_read)
            VALUES (%s, %s, %s, %s, 0)
        ''', (user_id, title, message, notification_type or 'general'))
        notification_id = cursor.lastrowid
        conn.commit()
        cursor.close(); conn.close(); return notification_id
    except Exception as exc:
        print(f'Create notification error: {exc}')
        return None


def get_all_user_ids():
    conn = get_db_connection('smart_study')
    if not conn:
        return []

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id FROM users ORDER BY id')
        rows = cursor.fetchall()
        cursor.close(); conn.close(); return [row['id'] for row in rows]
    except Exception as exc:
        print(f'Get all user ids error: {exc}')
        return []


def init_db():
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute('CREATE DATABASE IF NOT EXISTS smart_study')
        conn.commit()
        cursor.close()
        conn.close()

        conn = get_db_connection('smart_study')
        if conn is None:
            return False

        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255),
                password_hash VARCHAR(255),
                google_id VARCHAR(255),
                profile_picture VARCHAR(512),
                role VARCHAR(20) NOT NULL DEFAULT 'user',
                verification_code VARCHAR(100) NULL,
                is_verified BOOLEAN NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL
            )
        ''')

        try:
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user'")
            cursor.execute("UPDATE users SET role = 'user' WHERE role IS NULL OR role = ''")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_code VARCHAR(100) NULL")
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT 0")
            cursor.execute("UPDATE users SET is_verified = 0 WHERE is_verified IS NULL")
            cursor.execute("UPDATE users SET verification_code = NULL WHERE verification_code = ''")
        except Exception:
            pass

        # Create login_sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                token VARCHAR(255) UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Create user settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                notifications_assignments TINYINT(1) DEFAULT 1,
                notifications_messages TINYINT(1) DEFAULT 1,
                notifications_events TINYINT(1) DEFAULT 1,
                dark_mode TINYINT(1) DEFAULT 0,
                avatar_url VARCHAR(512),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        try:
            cursor.execute('ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS notifications_assignments TINYINT(1) DEFAULT 1')
            cursor.execute('ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS notifications_messages TINYINT(1) DEFAULT 1')
            cursor.execute('ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS notifications_events TINYINT(1) DEFAULT 1')
            cursor.execute('ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS dark_mode TINYINT(1) DEFAULT 0')
            cursor.execute('ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(512)')
        except Exception:
            pass

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                title VARCHAR(255),
                message TEXT,
                type VARCHAR(50) DEFAULT 'general',
                is_read TINYINT(1) DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                type VARCHAR(20) NOT NULL,
                name VARCHAR(255) NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_members (
                conversation_id INT NOT NULL,
                user_id INT NOT NULL,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (conversation_id, user_id),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                conversation_id INT NOT NULL,
                sender_id INT NOT NULL,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Create dashboard_data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dashboard_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                section VARCHAR(50) NOT NULL,
                payload JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Courses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                author VARCHAR(255),
                duration VARCHAR(100),
                description TEXT,
                type VARCHAR(20),
                resource_url VARCHAR(512),
                completed TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                event_time DATETIME NOT NULL,
                description TEXT NOT NULL,
                zoom_link VARCHAR(512) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Add resource_url if table exists without it
        try:
            cursor.execute('ALTER TABLE courses ADD COLUMN IF NOT EXISTS resource_url VARCHAR(512)')
            cursor.execute('ALTER TABLE courses ADD COLUMN IF NOT EXISTS completed TINYINT(1) DEFAULT 0')
        except Exception:
            pass

        # Assignments table (tasks)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                course_id INT,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                completed TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        ''')

        try:
            cursor.execute('ALTER TABLE assignments ADD COLUMN IF NOT EXISTS description TEXT')
        except Exception:
            pass

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignment_submissions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                assignment_id INT NOT NULL,
                user_id INT NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                stored_filename VARCHAR(255) NOT NULL,
                review_status VARCHAR(20) NOT NULL DEFAULT 'pending',
                feedback TEXT,
                reviewed_by INT NULL,
                reviewed_at DATETIME NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_assignment_user (assignment_id, user_id),
                FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        for column, definition in {
            'review_status': "VARCHAR(20) NOT NULL DEFAULT 'pending'",
            'feedback': 'TEXT',
            'reviewed_by': 'INT NULL',
            'reviewed_at': 'DATETIME NULL',
        }.items():
            try:
                cursor.execute(f'ALTER TABLE assignment_submissions ADD COLUMN IF NOT EXISTS {column} {definition}')
            except Exception:
                pass

        cursor.execute('SELECT COUNT(*) FROM dashboard_data')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO dashboard_data (section, payload) VALUES
                ('user', '{"name":"Jones"}'),
                ('categories', '[{"icon":"🎨","name":"Graphic Design","watched":8,"total":15},{"icon":"💻","name":"Coding","watched":2,"total":9},{"icon":"📈","name":"Marketing","watched":2,"total":9}]'),
                ('courses', '[{"category":"Coding","title":"Kursus Tiga","author":"John Doe","duration":"3 jam • Menengah","progress":55},{"category":"Coding","title":"Kursus Dua","author":"Michael Brown","duration":"2 jam • Pemula","progress":30},{"category":"Graphic Design","title":"Kursus Empat","author":"James Smith","duration":"3 jam • Ahli","progress":80}]'),
                ('progress', '{"completed":60,"inProgress":40,"notStarted":20}'),
                ('tasks', '[{"icon":"📌","title":"Mulai Tugas Satu","remaining":"3 hari 16 jam tersisa"},{"icon":"✏️","title":"Mulai Tugas Dua","remaining":"3 hari 20 jam tersisa"},{"icon":"📐","title":"Mulai Tugas Tiga","remaining":"4 hari 6 jam tersisa"}]')
            ''')
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error as exc:
        print(f'DB init error: {exc}')
        return False


def load_dashboard_from_db():
    conn = get_db_connection('smart_study')
    if conn is None:
        return None

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('USE smart_study')
        cursor.execute('SELECT section, payload FROM dashboard_data')
        rows = cursor.fetchall()
        data = {}
        for row in rows:
            payload = row['payload']
            if isinstance(payload, str):
                payload = json.loads(payload)
            if row['section'] == 'user':
                data['user'] = payload if isinstance(payload, dict) else {'name': 'Jones'}
            elif row['section'] == 'progress':
                data['progress'] = payload if isinstance(payload, dict) else {'completed': 60, 'inProgress': 40, 'notStarted': 20}
            else:
                data[row['section']] = payload
        return data
    except Exception as exc:
        print(f'Dashboard DB error: {exc}')
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


@app.route('/api/courses', methods=['GET', 'POST'])
def api_courses():
    if request.method == 'GET':
        conn = get_db_connection('smart_study')
        if not conn:
            return jsonify([]), 200
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT c.id, c.title, c.author, c.duration, c.description, c.type, c.resource_url,
                       c.completed,
                       COUNT(a.id) AS assignment_count
                FROM courses c
                LEFT JOIN assignments a ON a.course_id = c.id
                GROUP BY c.id
                ORDER BY c.created_at DESC
            ''')
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return jsonify(rows), 200
        except Exception as exc:
            print(f'Get courses error: {exc}')
            return jsonify([]), 200

    # POST -> create course
    user = get_user_by_id(session.get('user_id')) if session.get('user_id') else None
    if not user or str(user.get('role', 'user')).lower() != 'admin':
        return jsonify({'message': 'Hanya admin yang dapat menambah kursus.'}), 403

    data = request.get_json() or {}
    title = data.get('title')
    author = data.get('author')
    duration = data.get('duration')
    description = data.get('description')
    ctype = data.get('type', 'video')

    if not title:
        return jsonify({'message': 'Title required'}), 400

    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO courses (title, author, duration, description, type, resource_url) VALUES (%s,%s,%s,%s,%s,%s)'
                       , (title, author, duration, description, ctype, data.get('resource_url')))
        course_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'id': course_id}), 201
    except Exception as exc:
        print(f'Create course error: {exc}')
        return jsonify({'message': 'Create failed'}), 500


@app.route('/api/events', methods=['GET', 'POST'])
def api_events():
    if request.method == 'GET':
        conn = get_db_connection('smart_study')
        if not conn:
            return jsonify([]), 200
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT id, title, event_time, description, zoom_link
                FROM events
                ORDER BY event_time ASC
            ''')
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            for row in rows:
                event_time = row.pop('event_time')
                row['type'] = 'webinar'
                row['speaker'] = 'Admin Smart Study'
                row['date'] = event_time.strftime('%d %B %Y')
                row['time'] = event_time.strftime('%H:%M WIB')
                row['price'] = 'Gratis'
                row['link'] = row.pop('zoom_link')
            return jsonify(rows), 200
        except Exception as exc:
            print(f'Get events error: {exc}')
            return jsonify([]), 200

    if not session.get('user_id'):
        return jsonify({'message': 'Unauthorized'}), 401
    user = get_user_by_id(session['user_id'])
    if not user or str(user.get('role', 'user')).lower() != 'admin':
        return jsonify({'message': 'Hanya admin yang dapat menambah webinar.'}), 403

    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    event_time = (data.get('event_time') or '').strip()
    description = (data.get('description') or '').strip()
    zoom_link = (data.get('zoom_link') or '').strip()
    if not title or not event_time or not description or not zoom_link:
        return jsonify({'message': 'Judul, waktu, deskripsi, dan link Zoom wajib diisi.'}), 400
    if not zoom_link.startswith(('http://', 'https://')):
        return jsonify({'message': 'Link Zoom harus berupa URL yang valid.'}), 400

    try:
        parsed_time = datetime.fromisoformat(event_time)
    except ValueError:
        return jsonify({'message': 'Format waktu webinar tidak valid.'}), 400

    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO events (title, event_time, description, zoom_link) VALUES (%s, %s, %s, %s)',
            (title, parsed_time, description, zoom_link)
        )
        event_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'id': event_id, 'message': 'Webinar berhasil ditambahkan.'}), 201
    except Exception as exc:
        print(f'Create event error: {exc}')
        return jsonify({'message': 'Gagal menambahkan webinar.'}), 500


@app.route('/api/courses/<int:course_id>/complete', methods=['POST'])
def api_course_complete(course_id):
    user = get_user_by_id(session.get('user_id')) if session.get('user_id') else None
    if not user or str(user.get('role', 'user')).lower() != 'admin':
        return jsonify({'message': 'Hanya admin yang dapat mengubah kursus.'}), 403

    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT title, description, completed FROM courses WHERE id = %s', (course_id,))
        course = cursor.fetchone()
        if not course:
            cursor.close()
            conn.close()
            return jsonify({'message': 'Course not found'}), 404

        title = course.get('title', 'Materi')
        description = course.get('description', '')

        cursor.execute('SELECT COUNT(*) AS total FROM assignments WHERE course_id = %s', (course_id,))
        assignment_count = cursor.fetchone().get('total', 0)

        if not course.get('completed'):
            cursor.execute('UPDATE courses SET completed = 1 WHERE id = %s', (course_id,))

        if assignment_count == 0:
            task_title = f'Tugas: Kerjakan soal dari materi "{title}" untuk memperdalam pemahaman.'
            cursor.execute(
                'INSERT INTO assignments (course_id, title, description, completed) VALUES (%s,%s,%s,%s)',
                (course_id, task_title, description, 0)
            )
            conn.commit()
            for user_id in get_all_user_ids():
                create_notification(user_id, 'Tugas baru dibuat', f'Kursus "{title}" memiliki tugas baru yang siap dikerjakan.', 'tugas')
            cursor.close()
            conn.close()
            return jsonify({'message': 'Kursus selesai. Satu tugas otomatis ditambahkan ke Assignment.'}), 200

        cursor.close()
        conn.close()
        return jsonify({'message': 'Kursus sudah selesai dan tugas sudah tersedia di Assignment.'}), 200
    except Exception as exc:
        print(f'Course complete error: {exc}')
        return jsonify({'message': 'Failed'}), 500


@app.route('/api/courses/<int:course_id>/assignments', methods=['POST'])
def api_course_assignments(course_id):
    user = get_user_by_id(session.get('user_id')) if session.get('user_id') else None
    if not user or str(user.get('role', 'user')).lower() != 'admin':
        return jsonify({'message': 'Hanya admin yang dapat menambah tugas.'}), 403

    data = request.get_json() or {}
    title = data.get('title', '').strip()
    if not title:
        return jsonify({'message': 'Title required'}), 400

    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO assignments (course_id, title, description, completed) VALUES (%s,%s,%s,%s)', (course_id, title, '', 0))
        assignment_id = cursor.lastrowid
        conn.commit()

        course = cursor.execute('SELECT title FROM courses WHERE id = %s', (course_id,))
        course_title = None
        if course is not None:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT title FROM courses WHERE id = %s', (course_id,))
            course_row = cursor.fetchone()
            if course_row:
                course_title = course_row.get('title')

        for user_id in get_all_user_ids():
            create_notification(user_id, 'Tugas baru ditambahkan', f'{title} telah ditambahkan ke Assignment{f" pada kursus {course_title}" if course_title else ""}.', 'tugas')

        cursor.close()
        conn.close()
        return jsonify({'id': assignment_id}), 201
    except Exception as exc:
        print(f'Create assignment error: {exc}')
        return jsonify({'message': 'Failed'}), 500


@app.route('/api/assignments/<int:assignment_id>/questions', methods=['GET'])
def api_assignment_questions(assignment_id):
    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT a.id, a.title AS assignment_title, a.completed, c.id AS course_id,
                   c.title AS course_title, c.description, c.type, c.resource_url
            FROM assignments a
            LEFT JOIN courses c ON c.id = a.course_id
            WHERE a.id = %s
        ''', (assignment_id,))
        item = cursor.fetchone()
        cursor.close()
        conn.close()

        if not item:
            return jsonify({'message': 'Assignment not found'}), 404

        title = item['course_title'] or 'materi ini'
        description = item['description'] or ''
        source = item['resource_url'] or ''
        assignment_text = item['assignment_title']

        questions = [
            f'Apa tujuan utama dari materi "{title}"? Jelaskan dengan singkat.',
            f'Sebutkan dua poin penting yang perlu kamu ingat dari materi ini: "{description[:120]}".',
            f'Bagaimana kamu dapat menerapkan pembelajaran dari "{title}" dalam studi sehari-hari? Berikan satu contoh.',
            f'Jika kamu menggunakan sumber: {source or 'materi kursus'}, apa hal paling berguna yang kamu pelajari dari materi tersebut?'
        ]

        return jsonify({
            'assignment': {
                'id': item['id'],
                'title': assignment_text,
                'completed': bool(item['completed'])
            },
            'course_title': title,
            'questions': questions
        }), 200
    except Exception as exc:
        print(f'Get assignment questions error: {exc}')
        return jsonify({'message': 'Failed'}), 500


@app.route('/api/assignments', methods=['GET'])
def api_assignments():
    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify([]), 200
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT a.id, a.course_id, a.title, a.description, a.completed, c.title AS course_title,
                   s.original_filename AS submission_filename, s.submitted_at,
                   s.review_status, s.feedback
            FROM assignments a
            LEFT JOIN courses c ON c.id = a.course_id
            LEFT JOIN assignment_submissions s ON s.assignment_id = a.id AND s.user_id = %s
            ORDER BY a.created_at DESC
        ''', (session.get('user_id') or 0,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(rows), 200
    except Exception as exc:
        print(f'Get assignments error: {exc}')
        return jsonify([]), 200


def current_user_is_admin():
    user = get_user_by_id(session.get('user_id')) if session.get('user_id') else None
    return bool(user and str(user.get('role', 'user')).lower() == 'admin')


@app.route('/api/admin/assignments', methods=['POST'])
@admin_required
def api_admin_create_assignment():
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    description = (data.get('description') or '').strip()
    course_id = data.get('course_id') or None
    if not title:
        return jsonify({'message': 'Judul tugas wajib diisi.'}), 400

    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO assignments (course_id, title, description, completed) VALUES (%s, %s, %s, 0)',
            (course_id, title, description)
        )
        assignment_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        for user_id in get_all_user_ids():
            create_notification(user_id, 'Tugas baru ditambahkan', title, 'tugas')
        return jsonify({'id': assignment_id, 'message': 'Tugas berhasil ditambahkan.'}), 201
    except Exception as exc:
        print(f'Admin create assignment error: {exc}')
        return jsonify({'message': 'Gagal menambahkan tugas.'}), 500


@app.route('/api/admin/assignments/<int:assignment_id>', methods=['PUT'])
@admin_required
def api_admin_update_assignment(assignment_id):
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    description = (data.get('description') or '').strip()
    if not title:
        return jsonify({'message': 'Judul tugas wajib diisi.'}), 400

    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500
    try:
        cursor = conn.cursor()
        if 'course_id' in data:
            cursor.execute(
                'UPDATE assignments SET title = %s, description = %s, course_id = %s WHERE id = %s',
                (title, description, data.get('course_id') or None, assignment_id)
            )
        else:
            cursor.execute(
                'UPDATE assignments SET title = %s, description = %s WHERE id = %s',
                (title, description, assignment_id)
            )
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return jsonify({'message': 'Tugas tidak ditemukan.'}), 404
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Tugas berhasil diperbarui.'}), 200
    except Exception as exc:
        print(f'Admin update assignment error: {exc}')
        return jsonify({'message': 'Gagal memperbarui tugas.'}), 500


@app.route('/api/assignments/<int:assignment_id>/submit', methods=['POST'])
@require_login
def api_assignment_submit(assignment_id):
    uploaded_file = request.files.get('submission')
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({'message': 'Pilih file tugas terlebih dahulu.'}), 400

    original_filename = secure_filename(uploaded_file.filename)
    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id FROM assignments WHERE id = %s', (assignment_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'message': 'Tugas tidak ditemukan.'}), 404

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        user_id = session['user_id']
        stored_filename = f'{assignment_id}_{user_id}_{int(datetime.now().timestamp())}_{original_filename}'
        uploaded_file.save(UPLOAD_DIR / stored_filename)
        cursor.execute('''
            INSERT INTO assignment_submissions (assignment_id, user_id, original_filename, stored_filename)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE original_filename = VALUES(original_filename),
                                      stored_filename = VALUES(stored_filename),
                                      review_status = 'pending', feedback = NULL,
                                      reviewed_by = NULL, reviewed_at = NULL,
                                      submitted_at = CURRENT_TIMESTAMP
        ''', (assignment_id, user_id, original_filename, stored_filename))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Tugas berhasil dikumpulkan.', 'filename': original_filename}), 201
    except Exception as exc:
        print(f'Submit assignment error: {exc}')
        return jsonify({'message': 'Gagal mengumpulkan tugas.'}), 500


@app.route('/api/admin/assignment-submissions', methods=['GET'])
@admin_required
def api_admin_assignment_submissions():
    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify([]), 200
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT s.id, s.assignment_id, s.user_id, s.original_filename,
                   s.submitted_at, s.review_status, s.feedback,
                   a.title AS assignment_title, u.name AS user_name, u.email AS user_email
            FROM assignment_submissions s
            INNER JOIN assignments a ON a.id = s.assignment_id
            INNER JOIN users u ON u.id = s.user_id
            ORDER BY s.submitted_at DESC
        ''')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(rows), 200
    except Exception as exc:
        print(f'Get admin submissions error: {exc}')
        return jsonify([]), 200


@app.route('/api/admin/assignment-submissions/<int:submission_id>/file', methods=['GET'])
@admin_required
def api_admin_download_submission(submission_id):
    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT stored_filename, original_filename FROM assignment_submissions WHERE id = %s', (submission_id,))
        submission = cursor.fetchone()
        cursor.close()
        conn.close()
        if not submission:
            return jsonify({'message': 'Submission tidak ditemukan.'}), 404
        file_path = UPLOAD_DIR / submission['stored_filename']
        if not file_path.is_file():
            return jsonify({'message': 'File submission tidak ditemukan di server.'}), 404
        return send_from_directory(UPLOAD_DIR, submission['stored_filename'], as_attachment=True, download_name=submission['original_filename'])
    except Exception as exc:
        print(f'Download submission error: {exc}')
        return jsonify({'message': 'Gagal mengunduh file.'}), 500


@app.route('/api/admin/assignment-submissions/<int:submission_id>/review', methods=['PUT'])
@admin_required
def api_admin_review_submission(submission_id):
    data = request.get_json() or {}
    review_status = (data.get('review_status') or '').strip().lower()
    feedback = (data.get('feedback') or '').strip()
    if review_status not in {'correct', 'needs_revision'}:
        return jsonify({'message': 'Status review tidak valid.'}), 400

    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT s.user_id, s.feedback AS previous_feedback, a.title AS assignment_title
            FROM assignment_submissions s
            INNER JOIN assignments a ON a.id = s.assignment_id
            WHERE s.id = %s
        ''', (submission_id,))
        submission = cursor.fetchone()
        if not submission:
            cursor.close()
            conn.close()
            return jsonify({'message': 'Submission tidak ditemukan.'}), 404

        cursor.execute('''
            UPDATE assignment_submissions
            SET review_status = %s, feedback = %s, reviewed_by = %s, reviewed_at = NOW()
            WHERE id = %s
        ''', (review_status, feedback or None, session['user_id'], submission_id))
        conn.commit()
        cursor.close()
        conn.close()

        if feedback and feedback != (submission['previous_feedback'] or ''):
            create_notification(
                submission['user_id'],
                'Feedback tugas tersedia',
                f'Admin memberikan feedback untuk tugas "{submission["assignment_title"]}": {feedback}',
                'tugas'
            )

        return jsonify({'message': 'Review submission berhasil disimpan.'}), 200
    except Exception as exc:
        print(f'Review submission error: {exc}')
        return jsonify({'message': 'Gagal menyimpan review.'}), 500


@app.route('/api/assignments/<int:assignment_id>/complete', methods=['POST'])
def api_assignment_complete(assignment_id):
    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute('UPDATE assignments SET completed = 1 WHERE id = %s', (assignment_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Assignment marked complete'}), 200
    except Exception as exc:
        print(f'Complete assignment error: {exc}')
        return jsonify({'message': 'Failed'}), 500


@app.route('/api/assignments/<int:assignment_id>/reset', methods=['POST'])
def api_assignment_reset(assignment_id):
    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute('UPDATE assignments SET completed = 0 WHERE id = %s', (assignment_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Assignment reset to pending'}), 200
    except Exception as exc:
        print(f'Reset assignment error: {exc}')
        return jsonify({'message': 'Failed'}), 500


@app.route('/')
def index():
    if 'user_id' not in session:
        return send_from_directory(FRONTEND_DIR, 'login.html')
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return send_from_directory(FRONTEND_DIR, 'login.html')
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/login')
def login_page():
    if 'user_id' in session:
        return send_from_directory(FRONTEND_DIR, 'index.html')
    return send_from_directory(FRONTEND_DIR, 'login.html')


@app.route('/signup')
def signup_page():
    if 'user_id' in session:
        return send_from_directory(FRONTEND_DIR, 'index.html')
    return send_from_directory(FRONTEND_DIR, 'signup.html')


@app.route('/api/auth/status')
def auth_status():
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        role = (user or {}).get('role', 'user') if user else 'user'
        return jsonify({'authenticated': True, 'user_id': session['user_id'], 'role': role}), 200
    return jsonify({'authenticated': False, 'role': 'guest'}), 200


@app.route('/api/admin/users', methods=['GET'])
@admin_required
def api_admin_users():
    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify([]), 200

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id, name, email, role, verification_code, is_verified, created_at, last_login FROM users ORDER BY created_at DESC')
        rows = cursor.fetchall()
        cursor.close(); conn.close(); return jsonify(rows), 200
    except Exception as exc:
        print(f'Admin users error: {exc}')
        return jsonify([]), 200


@app.route('/api/admin/users', methods=['POST'])
@admin_required
def api_admin_create_user():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    name = (data.get('name') or '').strip()
    password = data.get('password') or ''
    password_confirm = data.get('password_confirm') or ''
    verification_code = (data.get('verification_code') or '').strip().upper()

    if not email or not name or not password or not password_confirm or not verification_code:
        return jsonify({'message': 'Nama, email, password, dan kode peserta wajib diisi'}), 400
    if '@' not in email or '.' not in email.rsplit('@', 1)[-1]:
        return jsonify({'message': 'Email tidak valid'}), 400
    if len(password) < 6:
        return jsonify({'message': 'Password minimal 6 karakter'}), 400
    if password != password_confirm:
        return jsonify({'message': 'Konfirmasi password tidak cocok'}), 400
    if get_user_by_email(email):
        return jsonify({'message': 'Email sudah terdaftar'}), 409

    user_id = create_user(
        email,
        name,
        password_hash=hash_password(password),
        verification_code=verification_code,
        is_verified=1,
    )
    if not user_id:
        return jsonify({'message': 'Gagal membuat akun peserta'}), 500

    return jsonify({
        'message': 'Akun peserta berhasil dibuat',
        'user': {
            'id': user_id,
            'email': email,
            'name': name,
            'role': 'user',
            'verification_code': verification_code,
        },
    }), 201


@app.route('/api/admin/users/<int:user_id>/verify', methods=['PUT'])
@admin_required
def api_admin_update_user_verification(user_id):
    data = request.get_json() or {}
    verification_code = (data.get('verification_code') or '').strip().upper()
    is_verified = bool(data.get('is_verified', True))

    if not verification_code:
        return jsonify({'message': 'Kode verifikasi wajib diisi'}), 400

    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500

    try:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET verification_code = %s, is_verified = %s WHERE id = %s', (verification_code, 1 if is_verified else 0, user_id))
        conn.commit(); cursor.close(); conn.close();
        return jsonify({'message': 'Kode verifikasi berhasil disimpan', 'verification_code': verification_code, 'is_verified': bool(is_verified)}), 200
    except Exception as exc:
        print(f'Admin update verification error: {exc}')
        return jsonify({'message': 'Failed'}), 500


@app.route('/api/admin/users/<int:user_id>/role', methods=['PUT'])
@admin_required
def api_admin_update_user_role(user_id):
    data = request.get_json() or {}
    role = (data.get('role') or 'user').strip().lower()
    if role not in {'admin', 'user'}:
        return jsonify({'message': 'Role tidak valid'}), 400

    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500

    try:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET role = %s WHERE id = %s', (role, user_id))
        conn.commit(); cursor.close(); conn.close();
        return jsonify({'message': 'Role berhasil diperbarui', 'role': role}), 200
    except Exception as exc:
        print(f'Admin update role error: {exc}')
        return jsonify({'message': 'Failed'}), 500


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = (data.get('email', '') or '').strip().lower()
    password = data.get('password', '')
    verification_code = (data.get('verification_code', '') or '').strip()
    role_selection_provided = 'account_role' in data
    requested_role = (data.get('account_role') or '').strip().lower()
    admin_code = (data.get('admin_code', '') or '').strip()
    remember_me = data.get('rememberMe', False)

    if not email or not password:
        return jsonify({'message': 'Email dan password harus diisi'}), 400

    user = get_user_by_email(email)
    
    if not user or not user['password_hash']:
        return jsonify({'message': 'Email atau password salah'}), 401

    if hash_password(password) != user['password_hash']:
        return jsonify({'message': 'Email atau password salah'}), 401

    role = str(user.get('role', 'user')).lower()
    if not requested_role:
        requested_role = role
    if requested_role not in {'admin', 'user'}:
        return jsonify({'message': 'Tipe akun tidak valid'}), 400
    if requested_role != role:
        return jsonify({'message': 'Pilihan akun tidak sesuai dengan akun ini.'}), 403

    if requested_role == 'admin' and role_selection_provided:
        if not admin_code or admin_code != ADMIN_CODE:
            return jsonify({'message': 'Kode admin tidak valid.'}), 403

    if role != 'admin':
        expected_code = str(user.get('verification_code') or '').strip().upper()
        if not expected_code:
            return jsonify({'message': 'Akun belum memiliki kode verifikasi. Hubungi admin.'}), 403
        if not verification_code:
            return jsonify({'message': 'Kode verifikasi wajib diisi untuk login.'}), 403
        if verification_code.strip().upper() != expected_code:
            return jsonify({'message': 'Kode verifikasi tidak valid.'}), 403

    # Login successful
    update_last_login(user['id'])
    session['user_id'] = user['id']
    session['email'] = user['email']
    session['name'] = user['name']
    session['role'] = role
    
    if remember_me:
        session.permanent = True
        app.permanent_session_lifetime = timedelta(days=30)

    return jsonify({
        'message': 'Login berhasil',
        'user': {
            'id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'role': role
        }
    }), 200


@app.route('/api/login/google', methods=['POST'])
def login_google():
    data = request.get_json()
    credential = data.get('credential')

    if not credential:
        return jsonify({'message': 'Credential tidak ditemukan'}), 400

    try:
        # Decode JWT token from Google
        parts = credential.split('.')
        if len(parts) != 3:
            return jsonify({'message': 'Invalid credential'}), 400

        # Decode payload (second part)
        payload = parts[1]
        # Add padding if necessary
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding

        decoded = base64.urlsafe_b64decode(payload)
        user_data = json.loads(decoded)

        email = user_data.get('email', '').lower()
        name = user_data.get('name', '')
        google_id = user_data.get('sub', '')
        picture = user_data.get('picture', '')

        if not email:
            return jsonify({'message': 'Email tidak ditemukan dari Google'}), 400

        # Check if user exists
        user = get_user_by_email(email)

        if not user:
            # Create new user
            user_id = create_user(email, name, google_id=google_id, profile_picture=picture)
            if not user_id:
                return jsonify({'message': 'Gagal membuat akun'}), 500
        else:
            user_id = user['id']
            update_last_login(user_id)

        # Create session
        session['user_id'] = user_id
        session['email'] = email
        session['name'] = name
        session['role'] = str((get_user_by_id(user_id) or {}).get('role', 'user')).lower()
        session.permanent = True
        app.permanent_session_lifetime = timedelta(days=30)

        return jsonify({
            'message': 'Login dengan Google berhasil',
            'user': {
                'id': user_id,
                'email': email,
                'name': name,
                'role': str((get_user_by_id(user_id) or {}).get('role', 'user')).lower()
            }
        }), 200

    except Exception as exc:
        print(f'Google login error: {exc}')
        return jsonify({'message': 'Gagal login dengan Google'}), 500


@app.route('/api/logout', methods=['POST', 'GET'])
def logout():
    session.clear()
    if request.method == 'GET':
        return redirect('/login')
    return jsonify({'message': 'Logout berhasil'}), 200


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = (data.get('email', '') or '').strip().lower()
    name = (data.get('name', '') or '').strip()
    password = data.get('password', '')
    password_confirm = data.get('password_confirm', '')
    requested_role = (data.get('account_role', 'user') or 'user').strip().lower()
    admin_code = (data.get('admin_code', '') or '').strip()

    if not email or not name or not password:
        return jsonify({'message': 'Semua field harus diisi'}), 400

    if password != password_confirm:
        return jsonify({'message': 'Password tidak cocok'}), 400

    if len(password) < 6:
        return jsonify({'message': 'Password minimal 6 karakter'}), 400

    if requested_role not in {'admin', 'user'}:
        return jsonify({'message': 'Tipe akun tidak valid'}), 400
    if requested_role == 'admin' and admin_code != ADMIN_CODE:
        return jsonify({'message': 'Kode admin tidak valid.'}), 403

    # Check if user exists
    user = get_user_by_email(email)
    if user:
        return jsonify({'message': 'Email sudah terdaftar'}), 409

    # Admin accounts are verified by the admin code; students need a code from an admin.
    password_hash = hash_password(password)
    user_id = create_user(email, name, password_hash=password_hash)

    if not user_id:
        return jsonify({'message': 'Gagal membuat akun'}), 500

    if requested_role == 'admin':
        conn = get_db_connection('smart_study')
        if conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET role = %s, is_verified = 1 WHERE id = %s', ('admin', user_id))
            conn.commit()
            cursor.close()
            conn.close()

    return jsonify({
        'message': 'Registrasi admin berhasil.' if requested_role == 'admin' else 'Registrasi berhasil. Tunggu kode verifikasi dari admin untuk login.',
        'user': {
            'id': user_id,
            'email': email,
            'name': name,
            'role': requested_role
        }
    }), 201


@app.route('/api/settings', methods=['GET'])
@require_login
def api_get_settings():
    user_id = session['user_id']
    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id, name, email, profile_picture FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            conn.close()
            return jsonify({'message': 'User not found'}), 404

        cursor.execute('SELECT * FROM user_settings WHERE user_id = %s', (user_id,))
        settings = cursor.fetchone() or {}

        response = {
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'avatar_url': user.get('profile_picture') or ''
            },
            'profile': {
                'name': user['name'],
                'email': user['email'],
                'avatar_url': user.get('profile_picture') or ''
            },
            'settings': {
                'assignments': bool(settings.get('notifications_assignments', True)),
                'messages': bool(settings.get('notifications_messages', True)),
                'events': bool(settings.get('notifications_events', True)),
                'dark_mode': bool(settings.get('dark_mode', False)),
                'theme': 'dark' if settings.get('dark_mode', False) else 'light',
                'avatar_url': user.get('profile_picture') or ''
            }
        }
        cursor.close()
        conn.close()
        return jsonify(response), 200
    except Exception as exc:
        print(f'Get settings error: {exc}')
        return jsonify({'message': 'Failed'}), 500


@app.route('/api/settings/profile', methods=['PUT'])
@require_login
def api_update_profile():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    avatar_url = (data.get('avatar_url') or '').strip()

    if not name or not email:
        return jsonify({'message': 'Nama dan email wajib diisi'}), 400

    user_id = session['user_id']
    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id FROM users WHERE email = %s AND id != %s', (email, user_id))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'message': 'Email sudah digunakan'}), 409

        cursor.execute('UPDATE users SET name = %s, email = %s, profile_picture = %s WHERE id = %s',
                       (name, email, avatar_url or None, user_id))

        cursor.execute('SELECT * FROM user_settings WHERE user_id = %s', (user_id,))
        settings = cursor.fetchone() or {}
        if not settings:
            cursor.execute(
                'INSERT INTO user_settings (user_id, notifications_assignments, notifications_messages, notifications_events, dark_mode, avatar_url) VALUES (%s, %s, %s, %s, %s, %s)',
                (user_id, True, True, True, False, avatar_url or None)
            )
        else:
            cursor.execute(
                'UPDATE user_settings SET avatar_url = %s, updated_at = NOW() WHERE user_id = %s',
                (avatar_url or settings.get('avatar_url'), user_id)
            )

        conn.commit()
        cursor.close()
        conn.close()

        session['name'] = name
        session['email'] = email

        return jsonify({
            'message': 'Profil berhasil diperbarui',
            'user': {'id': user_id, 'name': name, 'email': email, 'avatar_url': avatar_url or ''}
        }), 200
    except Exception as exc:
        print(f'Update profile error: {exc}')
        return jsonify({'message': 'Failed'}), 500


@app.route('/api/settings/password', methods=['PUT'])
@require_login
def api_update_password():
    data = request.get_json() or {}
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not old_password or not new_password or not confirm_password:
        return jsonify({'message': 'Semua field password wajib diisi'}), 400

    if new_password != confirm_password:
        return jsonify({'message': 'Konfirmasi password tidak cocok'}), 400

    if len(new_password) < 6:
        return jsonify({'message': 'Password minimal 6 karakter'}), 400

    user_id = session['user_id']
    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT password_hash FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        if not user or hash_password(old_password) != user['password_hash']:
            cursor.close()
            conn.close()
            return jsonify({'message': 'Password lama tidak sesuai'}), 400

        cursor.execute('UPDATE users SET password_hash = %s WHERE id = %s', (hash_password(new_password), user_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Password berhasil diperbarui'}), 200
    except Exception as exc:
        print(f'Update password error: {exc}')
        return jsonify({'message': 'Failed'}), 500


@app.route('/api/settings/notifications', methods=['PUT'])
@require_login
def api_update_notifications():
    data = request.get_json() or {}
    assignments = bool(data.get('assignments', True))
    messages = bool(data.get('messages', True))
    events = bool(data.get('events', True))
    dark_mode = bool(data.get('dark_mode', False))

    user_id = session['user_id']
    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM user_settings WHERE user_id = %s', (user_id,))
        settings = cursor.fetchone()
        if settings:
            cursor.execute('''
                UPDATE user_settings
                SET notifications_assignments = %s,
                    notifications_messages = %s,
                    notifications_events = %s,
                    dark_mode = %s,
                    updated_at = NOW()
                WHERE user_id = %s
            ''', (int(assignments), int(messages), int(events), int(dark_mode), user_id))
        else:
            cursor.execute('''
                INSERT INTO user_settings (user_id, notifications_assignments, notifications_messages, notifications_events, dark_mode)
                VALUES (%s, %s, %s, %s, %s)
            ''', (user_id, int(assignments), int(messages), int(events), int(dark_mode)))

        response = {
            'assignments': assignments,
            'messages': messages,
            'events': events,
            'dark_mode': dark_mode,
            'theme': 'dark' if dark_mode else 'light'
        }
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Preferensi berhasil disimpan', 'settings': response}), 200
    except Exception as exc:
        print(f'Update notifications error: {exc}')
        return jsonify({'message': 'Failed'}), 500


@app.route('/api/notifications', methods=['GET'])
@require_login
def api_notifications():
    user_id = session['user_id']
    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify([]), 200

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT id, user_id, title, message, type, is_read, created_at
            FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
        ''', (user_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(rows), 200
    except Exception as exc:
        print(f'Get notifications error: {exc}')
        return jsonify([]), 200


@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@require_login
def api_notification_read(notification_id):
    user_id = session['user_id']
    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500

    try:
        cursor = conn.cursor()
        cursor.execute('UPDATE notifications SET is_read = 1 WHERE id = %s AND user_id = %s', (notification_id, user_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Notification marked as read'}), 200
    except Exception as exc:
        print(f'Read notification error: {exc}')
        return jsonify({'message': 'Failed'}), 500


@app.route('/api/notifications/read-all', methods=['POST'])
@require_login
def api_notifications_read_all():
    user_id = session['user_id']
    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500

    try:
        cursor = conn.cursor()
        cursor.execute('UPDATE notifications SET is_read = 1 WHERE user_id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'All notifications marked as read'}), 200
    except Exception as exc:
        print(f'Read all notification error: {exc}')
        return jsonify({'message': 'Failed'}), 500


@app.route('/api/users', methods=['GET'])
@require_login
def api_users():
    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify([]), 200

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id, name, email FROM users WHERE id != %s ORDER BY name ASC', (session['user_id'],))
        rows = cursor.fetchall()
        cursor.close(); conn.close(); return jsonify(rows), 200
    except Exception as exc:
        print(f'Get users error: {exc}')
        return jsonify([]), 200


@app.route('/api/conversations', methods=['GET', 'POST'])
@require_login
def api_conversations():
    user_id = session['user_id']
    if request.method == 'GET':
        conn = get_db_connection('smart_study')
        if not conn:
            return jsonify([]), 200

        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT c.id, c.type, c.name,
                       (SELECT m.content FROM messages m WHERE m.conversation_id = c.id ORDER BY m.created_at DESC LIMIT 1) AS last_message,
                       (SELECT m.created_at FROM messages m WHERE m.conversation_id = c.id ORDER BY m.created_at DESC LIMIT 1) AS last_message_at,
                       (SELECT u.name FROM messages m2 JOIN users u ON u.id = m2.sender_id WHERE m2.conversation_id = c.id ORDER BY m2.created_at DESC LIMIT 1) AS last_sender_name
                FROM conversations c
                JOIN conversation_members cm ON cm.conversation_id = c.id
                WHERE cm.user_id = %s
                ORDER BY last_message_at DESC, c.created_at DESC
            ''', (user_id,))
            rows = cursor.fetchall()
            cursor.close(); conn.close(); return jsonify(rows), 200
        except Exception as exc:
            print(f'Get conversations error: {exc}')
            return jsonify([]), 200

    data = request.get_json() or {}
    conversation_type = (data.get('type') or 'private').strip().lower()
    member_ids = data.get('member_ids') or []
    name = (data.get('name') or '').strip()

    if conversation_type not in ('private', 'group'):
        return jsonify({'message': 'Tipe percakapan tidak valid'}), 400

    if conversation_type == 'group' and not name:
        return jsonify({'message': 'Nama grup wajib diisi'}), 400

    unique_member_ids = []
    seen = set()
    for member_id in member_ids:
        member_id = int(member_id)
        if member_id not in seen and member_id != user_id:
            seen.add(member_id)
            unique_member_ids.append(member_id)

    if conversation_type == 'private':
        if len(unique_member_ids) == 0:
            return jsonify({'message': 'Pilih satu user lain untuk chat pribadi'}), 400
        if len(unique_member_ids) > 1:
            return jsonify({'message': 'Chat pribadi hanya boleh 1 lawan bicara'}), 400

    final_members = {user_id} | set(unique_member_ids)
    if len(final_members) < 2:
        return jsonify({'message': 'Percakapan harus memiliki minimal 2 orang'}), 400

    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        if conversation_type == 'private':
            other_user_id = next(iter(unique_member_ids))
            cursor.execute('''
                SELECT c.id
                FROM conversations c
                JOIN conversation_members cm1 ON cm1.conversation_id = c.id
                JOIN conversation_members cm2 ON cm2.conversation_id = c.id
                WHERE c.type = 'private' AND cm1.user_id = %s AND cm2.user_id = %s
                GROUP BY c.id
                LIMIT 1
            ''', (user_id, other_user_id))
            existing = cursor.fetchone()
            if existing:
                cursor.close(); conn.close();
                return jsonify({'message': 'Percakapan pribadi sudah ada', 'conversation': {'id': existing['id'], 'type': 'private'}}), 200

        cursor.execute('INSERT INTO conversations (type, name) VALUES (%s, %s)', (conversation_type, name or None))
        conversation_id = cursor.lastrowid
        for member_id in sorted(final_members):
            cursor.execute('INSERT INTO conversation_members (conversation_id, user_id) VALUES (%s, %s)', (conversation_id, member_id))
        conn.commit()
        cursor.close(); conn.close();
        return jsonify({'message': 'Percakapan dibuat', 'conversation': {'id': conversation_id, 'type': conversation_type, 'name': name or None}}), 201
    except Exception as exc:
        print(f'Create conversation error: {exc}')
        return jsonify({'message': 'Failed'}), 500


@app.route('/api/conversations/<int:conversation_id>/messages', methods=['GET', 'POST'])
@require_login
def api_conversation_messages(conversation_id):
    user_id = session['user_id']
    conn = get_db_connection('smart_study')
    if not conn:
        return jsonify({'message': 'DB connection failed'}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT 1 FROM conversation_members WHERE conversation_id = %s AND user_id = %s', (conversation_id, user_id))
        membership = cursor.fetchone()
        if not membership:
            cursor.close(); conn.close();
            return jsonify({'message': 'Forbidden'}), 403

        if request.method == 'GET':
            cursor.execute('''
                SELECT m.id, m.conversation_id, m.sender_id, u.name AS sender_name, m.content, m.created_at
                FROM messages m
                JOIN users u ON u.id = m.sender_id
                WHERE m.conversation_id = %s
                ORDER BY m.created_at ASC
            ''', (conversation_id,))
            rows = cursor.fetchall()
            cursor.close(); conn.close();
            return jsonify({'messages': rows}), 200

        data = request.get_json() or {}
        content = (data.get('content') or '').strip()
        if not content:
            cursor.close(); conn.close();
            return jsonify({'message': 'Isi pesan tidak boleh kosong'}), 400

        cursor.execute('SELECT c.type, c.name, u.name AS sender_name FROM conversations c JOIN users u ON u.id = %s WHERE c.id = %s', (user_id, conversation_id))
        conversation_meta = cursor.fetchone()
        if not conversation_meta:
            cursor.close(); conn.close();
            return jsonify({'message': 'Conversation not found'}), 404

        cursor.execute('INSERT INTO messages (conversation_id, sender_id, content) VALUES (%s, %s, %s)', (conversation_id, user_id, content))
        message_id = cursor.lastrowid

        cursor.execute('SELECT user_id FROM conversation_members WHERE conversation_id = %s AND user_id != %s', (conversation_id, user_id))
        recipients = cursor.fetchall()
        sender_name = conversation_meta.get('sender_name', 'Seseorang')
        conversation_name = conversation_meta.get('name') or 'Percakapan'
        for row in recipients:
            create_notification(row['user_id'], 'Pesan baru', f'{sender_name} mengirim pesan di {conversation_name}.', 'pesan')

        conn.commit(); cursor.close(); conn.close();
        return jsonify({'message': 'Pesan terkirim', 'id': message_id}), 201
    except Exception as exc:
        print(f'Conversation messages error: {exc}')
        return jsonify({'message': 'Failed'}), 500


@app.route('/api/dashboard')
@require_login
def dashboard_api():
    data = load_dashboard_from_db()
    if data:
        # Add user info from session
        data['user'] = {
            'name': session.get('name', 'User'),
            'email': session.get('email', '')
        }
        return jsonify(data)
    return jsonify(get_default_dashboard()), 200


@app.route('/<path:filename>')
def frontend_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


init_db()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)