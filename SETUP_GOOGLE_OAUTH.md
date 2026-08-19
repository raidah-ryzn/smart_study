# Setup Google OAuth di MyCourse

## Langkah 1: Setup Google OAuth 2.0

1. Buka https://console.cloud.google.com/
2. Login dengan akun Google Anda
3. Buat project baru atau gunakan project yang sudah ada
4. Di menu Navigation, pilih "APIs & Services" > "Credentials"
5. Klik "Create Credentials" > "OAuth client ID"
6. Pilih "Web application"
7. Di "Authorized redirect URIs", tambahkan:
   - http://localhost:5000
   - http://localhost:5000/
   - http://localhost:5000/login

8. Copy "Client ID" Anda

## Langkah 2: Setup di Aplikasi

### 1. Update login.html
Buka `.frontend/login.html` dan ganti:
```
YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com
```
Dengan Client ID yang sudah Anda copy

Dua tempat yang perlu diganti:
- Line 7: `<meta name="google-signin-client_id" content="YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com" />`
- Line 114: `data-client_id="YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"`

### 2. Environment Variables (Optional)
Anda bisa juga set environment variable (lebih aman untuk production):
```bash
set GOOGLE_CLIENT_ID=your-client-id-here
```

## Langkah 3: Test Login

1. Jalankan server Flask:
```bash
python hallo.py
```

2. Buka http://localhost:5000/login di browser

3. Test dengan:
   - **Email/Password**: 
     - Email: test@example.com
     - Password: password123 (minimal 6 karakter)
   
   - **Google Sign In**: 
     - Klik tombol "Sign in with Google"
     - Login dengan akun Google Anda

## Database Tables

Aplikasi akan otomatis membuat tabel:
- `users`: Menyimpan data user (email, name, password_hash, google_id, etc)
- `login_sessions`: Menyimpan session login
- `dashboard_data`: Menyimpan data dashboard

## Fitur-fitur Login

✅ Email/Password login
✅ Google OAuth Sign In  
✅ "Remember Me" functionality
✅ Password visibility toggle
✅ Form validation
✅ Error handling
✅ Session management
✅ Protected routes (dashboard hanya bisa diakses login)
✅ Auto redirect ke login jika belum login
✅ Auto redirect ke dashboard jika sudah login

## Notes

- Password di-hash menggunakan SHA256 sebelum disimpan ke database
- Session default berlaku 1 hari, bisa diperpanjang dengan "Remember Me"
- Database MySQL harus aktif (XAMPP)
- Semua error message user-friendly dan dalam Bahasa Indonesia
