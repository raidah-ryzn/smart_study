#!/usr/bin/env python3
"""
Setup test user untuk demo aplikasi MyCourse
Jalankan: python setup_test_user.py
"""

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
                'password': 'demo123'
            },
            {
                'email': 'john@example.com',
                'name': 'John Doe',
                'password': 'password123'
            },
            {
                'email': 'jane@example.com',
                'name': 'Jane Smith',
                'password': 'password123'
            }
        ]
        
        for user in test_users:
            password_hash = hash_password(user['password'])
            
            # Check if user exists
            cursor.execute('SELECT id FROM users WHERE email = %s', (user['email'],))
            if cursor.fetchone():
                print(f"✓ User {user['email']} sudah ada")
            else:
                cursor.execute(
                    'INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s)',
                    (user['email'], user['name'], password_hash)
                )
                print(f"✓ User {user['email']} berhasil ditambahkan")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n✅ Setup selesai!")
        print("\nTest credentials:")
        for user in test_users:
            print(f"  Email: {user['email']}")
            print(f"  Password: {user['password']}\n")
        
    except Error as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    setup_test_users()
