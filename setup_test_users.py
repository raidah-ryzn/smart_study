#!/usr/bin/env python3
"""Script untuk setup test user di database MySQL"""

import hashlib
import mysql.connector
from mysql.connector import Error

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def setup_test_users():
    try:
        conn = mysql.connector.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='',
            database='smart_study',
            autocommit=True
        )
        cursor = conn.cursor()

        # Test users
        test_users = [
            {
                'email': 'demo@example.com',
                'name': 'Demo User',
                'password': 'password123'
            },
            {
                'email': 'test@example.com',
                'name': 'Test User',
                'password': 'test1234'
            },
            {
                'email': 'admin@mycourse.com',
                'name': 'Admin MyCourse',
                'password': 'admin1234'
            }
        ]

        for user in test_users:
            password_hash = hash_password(user['password'])
            
            # Check if user exists
            cursor.execute('SELECT id FROM users WHERE email = %s', (user['email'],))
            if cursor.fetchone():
                print(f"User {user['email']} sudah ada")
                continue
            
            # Create user
            cursor.execute('''
                INSERT INTO users (email, name, password_hash, created_at, last_login)
                VALUES (%s, %s, %s, NOW(), NOW())
            ''', (user['email'], user['name'], password_hash))
            print(f"✅ User {user['email']} berhasil dibuat")
            print(f"   Password: {user['password']}")

        conn.commit()
        cursor.close()
        conn.close()
        print("\n✅ Setup test users selesai!")

    except Error as exc:
        print(f"❌ Error: {exc}")
        return False
    
    return True

if __name__ == '__main__':
    setup_test_users()
