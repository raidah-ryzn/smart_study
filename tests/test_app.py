import unittest
import json
import uuid

from hallo import app


class DashboardAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        app.config['TESTING'] = True

    def test_login_page_loads(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Selamat Datang", response.data)

    def test_api_dashboard_requires_login(self):
        response = self.client.get("/api/dashboard")
        self.assertEqual(response.status_code, 401)

    def test_register_new_user(self):
        test_email = f"{uuid.uuid4().hex}@example.com"
        response = self.client.post("/api/register", 
            json={
                "email": test_email,
                "name": "Test User",
                "password": "password123",
                "password_confirm": "password123"
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn("user", data)
        self.assertEqual(data["user"]["email"], test_email)

    def test_login_with_email_password(self):
        email = "login_test@example.com"
        self.client.post("/api/register", 
            json={
                "email": email,
                "name": "Login Test",
                "password": "password123",
                "password_confirm": "password123"
            },
            content_type="application/json"
        )

        from hallo import get_db_connection
        conn = get_db_connection('smart_study')
        self.assertIsNotNone(conn)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET verification_code = 'APPROVED-1', is_verified = 1 WHERE email = %s", (email,))
        conn.commit()
        cursor.close(); conn.close()

        response = self.client.post("/api/login",
            json={
                "email": email,
                "password": "password123",
                "verification_code": "APPROVED-1",
                "rememberMe": False
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("user", data)
        self.assertEqual(data["user"]["email"], email)

    def test_login_with_wrong_password(self):
        # First register
        self.client.post("/api/register", 
            json={
                "email": "wrong_pw@example.com",
                "name": "Wrong PW Test",
                "password": "password123",
                "password_confirm": "password123"
            },
            content_type="application/json"
        )
        
        # Try login with wrong password
        response = self.client.post("/api/login",
            json={
                "email": "wrong_pw@example.com",
                "password": "wrongpassword",
                "rememberMe": False
            },
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    def test_auth_status_not_authenticated(self):
        response = self.client.get("/api/auth/status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data["authenticated"])

    def test_redirect_to_login_when_not_authenticated(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Selamat Datang", response.data)  # Should load login page

    def test_settings_profile_and_notifications_require_login(self):
        response = self.client.get("/api/settings")
        self.assertEqual(response.status_code, 401)

        response = self.client.put("/api/settings/profile", json={"name": "Updated", "email": "updated@example.com"})
        self.assertEqual(response.status_code, 401)

    def test_settings_profile_and_password_update_after_login(self):
        email = f"settings_user_{uuid.uuid4().hex}@example.com"
        new_email = f"newname_{uuid.uuid4().hex}@example.com"

        self.client.post("/api/register",
            json={
                "email": email,
                "name": "Settings User",
                "password": "password123",
                "password_confirm": "password123"
            },
            content_type="application/json"
        )

        from hallo import get_db_connection
        conn = get_db_connection('smart_study')
        self.assertIsNotNone(conn)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET verification_code = 'SETTINGS-1', is_verified = 1 WHERE email = %s", (email,))
        conn.commit()
        cursor.close(); conn.close()

        login_res = self.client.post("/api/login",
            json={
                "email": email,
                "password": "password123",
                "verification_code": "SETTINGS-1",
                "rememberMe": False
            },
            content_type="application/json"
        )
        self.assertEqual(login_res.status_code, 200)

        profile_res = self.client.put("/api/settings/profile",
            json={
                "name": "New Name",
                "email": new_email
            },
            content_type="application/json"
        )
        self.assertEqual(profile_res.status_code, 200)
        self.assertEqual(profile_res.get_json()["user"]["name"], "New Name")

        password_res = self.client.put("/api/settings/password",
            json={
                "old_password": "password123",
                "new_password": "newpass456",
                "confirm_password": "newpass456"
            },
            content_type="application/json"
        )
        self.assertEqual(password_res.status_code, 200)

        notifications_res = self.client.put("/api/settings/notifications",
            json={
                "assignments": False,
                "messages": True,
                "events": False,
                "dark_mode": True
            },
            content_type="application/json"
        )
        self.assertEqual(notifications_res.status_code, 200)
        self.assertFalse(notifications_res.get_json()["settings"]["assignments"])
        self.assertTrue(notifications_res.get_json()["settings"]["dark_mode"])

    def test_notifications_api_and_helper(self):
        email = f"notif_user_{uuid.uuid4().hex}@example.com"
        self.client.post("/api/register",
            json={
                "email": email,
                "name": "Notif User",
                "password": "password123",
                "password_confirm": "password123"
            },
            content_type="application/json"
        )

        from hallo import get_db_connection
        conn = get_db_connection('smart_study')
        self.assertIsNotNone(conn)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET verification_code = 'NOTIF-1', is_verified = 1 WHERE email = %s", (email,))
        conn.commit()
        cursor.close(); conn.close()

        login_res = self.client.post("/api/login",
            json={
                "email": email,
                "password": "password123",
                "verification_code": "NOTIF-1",
                "rememberMe": False
            },
            content_type="application/json"
        )
        self.assertEqual(login_res.status_code, 200)

        user_id = login_res.get_json()['user']['id']
        from hallo import create_notification
        created = create_notification(user_id, 'Tugas baru', 'Ada tugas baru untuk Anda.', 'tugas')
        self.assertIsNotNone(created)

        list_res = self.client.get('/api/notifications')
        self.assertEqual(list_res.status_code, 200)
        self.assertGreater(len(list_res.get_json()), 0)

        unread_before = len([n for n in list_res.get_json() if not n['is_read']])
        read_all_res = self.client.post('/api/notifications/read-all')
        self.assertEqual(read_all_res.status_code, 200)

        list_after = self.client.get('/api/notifications')
        self.assertEqual(len([n for n in list_after.get_json() if not n['is_read']]), 0)
        self.assertGreaterEqual(unread_before, 1)

    def test_private_chat_conversation_and_messages(self):
        user_a_email = f"chat_a_{uuid.uuid4().hex}@example.com"
        user_b_email = f"chat_b_{uuid.uuid4().hex}@example.com"
        self.client.post('/api/register', json={'email': user_a_email, 'name': 'Chat A', 'password': 'password123', 'password_confirm': 'password123'}, content_type='application/json')
        self.client.post('/api/register', json={'email': user_b_email, 'name': 'Chat B', 'password': 'password123', 'password_confirm': 'password123'}, content_type='application/json')

        from hallo import get_db_connection
        conn = get_db_connection('smart_study')
        self.assertIsNotNone(conn)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET verification_code = 'CHAT-A', is_verified = 1 WHERE email = %s", (user_a_email,))
        cursor.execute("UPDATE users SET verification_code = 'CHAT-B', is_verified = 1 WHERE email = %s", (user_b_email,))
        conn.commit()
        cursor.close(); conn.close()

        login_a = self.client.post('/api/login', json={'email': user_a_email, 'password': 'password123', 'verification_code': 'CHAT-A', 'rememberMe': False}, content_type='application/json')
        self.assertEqual(login_a.status_code, 200)
        user_a_id = login_a.get_json()['user']['id']

        login_b = self.client.post('/api/login', json={'email': user_b_email, 'password': 'password123', 'verification_code': 'CHAT-B', 'rememberMe': False}, content_type='application/json')
        self.assertEqual(login_b.status_code, 200)
        user_b_id = login_b.get_json()['user']['id']

        self.client.post('/api/logout', content_type='application/json')
        self.client.post('/api/login', json={'email': user_a_email, 'password': 'password123', 'verification_code': 'CHAT-A', 'rememberMe': False}, content_type='application/json')

        create = self.client.post('/api/conversations', json={'type': 'private', 'member_ids': [user_b_id]}, content_type='application/json')
        self.assertEqual(create.status_code, 201)
        conversation = create.get_json()
        conversation_id = conversation['conversation']['id']

        send = self.client.post(f'/api/conversations/{conversation_id}/messages', json={'content': 'Halo dari A'}, content_type='application/json')
        self.assertEqual(send.status_code, 201)

        list_res = self.client.get('/api/conversations')
        self.assertEqual(list_res.status_code, 200)
        self.assertTrue(any(item['id'] == conversation_id for item in list_res.get_json()))

        messages_res = self.client.get(f'/api/conversations/{conversation_id}/messages')
        self.assertEqual(messages_res.status_code, 200)
        data = messages_res.get_json()
        self.assertTrue(any(msg['content'] == 'Halo dari A' for msg in data['messages']))

    def test_user_requires_verification_code_for_login(self):
        email = f"verify_user_{uuid.uuid4().hex}@example.com"
        register = self.client.post('/api/register', json={
            'email': email,
            'name': 'Pending User',
            'password': 'password123',
            'password_confirm': 'password123'
        }, content_type='application/json')
        self.assertEqual(register.status_code, 201)

        from hallo import get_db_connection
        conn = get_db_connection('smart_study')
        self.assertIsNotNone(conn)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET verification_code = 'KODE-123', is_verified = 0 WHERE email = %s", (email,))
        conn.commit()
        cursor.close(); conn.close()

        denied = self.client.post('/api/login', json={
            'email': email,
            'password': 'password123',
            'verification_code': 'WRONG-999',
            'rememberMe': False
        }, content_type='application/json')
        self.assertEqual(denied.status_code, 403)

        approved = self.client.post('/api/login', json={
            'email': email,
            'password': 'password123',
            'verification_code': 'KODE-123',
            'rememberMe': False
        }, content_type='application/json')
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.get_json()['user']['email'], email)

    def test_role_admin_and_auth_status_include_role(self):
        email = f"admin_user_{uuid.uuid4().hex}@example.com"
        register = self.client.post('/api/register', json={
            'email': email,
            'name': 'Admin Role User',
            'password': 'password123',
            'password_confirm': 'password123'
        }, content_type='application/json')
        self.assertEqual(register.status_code, 201)

        from hallo import get_db_connection
        conn = get_db_connection('smart_study')
        self.assertIsNotNone(conn)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = 'admin', verification_code = 'ADMIN-OK', is_verified = 1 WHERE email = %s", (email,))
        conn.commit()
        cursor.close(); conn.close()

        login = self.client.post('/api/login', json={
            'email': email,
            'password': 'password123',
            'verification_code': 'ADMIN-OK',
            'rememberMe': False
        }, content_type='application/json')
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.get_json()['user']['role'], 'admin')

        status = self.client.get('/api/auth/status')
        self.assertEqual(status.status_code, 200)
        self.assertIn('role', status.get_json())
        self.assertEqual(status.get_json()['role'], 'admin')

        admin_users = self.client.get('/api/admin/users')
        self.assertEqual(admin_users.status_code, 200)
        self.assertGreater(len(admin_users.get_json()), 0)

        self.client.post('/api/logout', content_type='application/json')
        normal_user = self.client.post('/api/register', json={
            'email': f"normal_user_{uuid.uuid4().hex}@example.com",
            'name': 'Normal User',
            'password': 'password123',
            'password_confirm': 'password123'
        }, content_type='application/json')
        self.assertEqual(normal_user.status_code, 201)

        from hallo import get_db_connection as gdb
        c = gdb('smart_study')
        cur = c.cursor()
        cur.execute("UPDATE users SET verification_code = 'USER-OK', is_verified = 1 WHERE email = %s", (normal_user.get_json()['user']['email'],))
        c.commit(); cur.close(); c.close()

        user_login = self.client.post('/api/login', json={
            'email': normal_user.get_json()['user']['email'],
            'password': 'password123',
            'verification_code': 'USER-OK',
            'rememberMe': False
        }, content_type='application/json')
        self.assertEqual(user_login.status_code, 200)

        user_status = self.client.get('/api/auth/status')
        self.assertEqual(user_status.get_json()['role'], 'user')
        forbidden = self.client.get('/api/admin/users')
        self.assertEqual(forbidden.status_code, 403)

