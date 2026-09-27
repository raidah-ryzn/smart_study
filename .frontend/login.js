// login.js — Handle login form dan Google Sign In

// Toggle password visibility
const togglePasswordBtn = document.getElementById('toggle-password');
const passwordInput = document.getElementById('password');

if (togglePasswordBtn) {
  togglePasswordBtn.addEventListener('click', (e) => {
    e.preventDefault();
    const type = passwordInput.type === 'password' ? 'text' : 'password';
    passwordInput.type = type;
    togglePasswordBtn.textContent = type === 'password' ? '👁' : '🙈';
  });
}

// Show alert message
function showAlert(message, type = 'error') {
  const alertDiv = document.getElementById('alert-message');
  alertDiv.textContent = message;
  alertDiv.className = `alert ${type}`;
  alertDiv.style.display = 'block';
  
  if (type === 'success') {
    setTimeout(() => {
      alertDiv.style.display = 'none';
    }, 2000);
  }
}

// Clear error messages
function clearErrors() {
  document.getElementById('email-error').textContent = '';
  document.getElementById('password-error').textContent = '';
  const adminCodeError = document.getElementById('admin-code-error');
  if (adminCodeError) adminCodeError.textContent = '';
  const vcError = document.getElementById('verification-code-error');
  if (vcError) vcError.textContent = '';
  document.getElementById('alert-message').style.display = 'none';
}

// Validate email
function validateEmail(email) {
  const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return regex.test(email);
}

// Validate password
function validatePassword(password) {
  return password.length >= 6;
}

// Handle form submission
const loginForm = document.getElementById('login-form');
const accountRole = document.getElementById('account-role');
const adminCodeGroup = document.getElementById('admin-code-group');
const adminCodeInput = document.getElementById('admin-code');
const verificationCodeGroup = document.getElementById('verification-code-group');

function updateRoleFields() {
  const isAdmin = accountRole && accountRole.value === 'admin';
  if (adminCodeGroup) adminCodeGroup.classList.toggle('hidden', !isAdmin);
  if (adminCodeInput) adminCodeInput.required = Boolean(isAdmin);
  if (verificationCodeGroup) verificationCodeGroup.classList.toggle('hidden', Boolean(isAdmin));
}

if (accountRole) {
  accountRole.addEventListener('change', updateRoleFields);
  updateRoleFields();
}

if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearErrors();

    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const verificationCode = document.getElementById('verification-code') ? document.getElementById('verification-code').value.trim() : '';
    const selectedRole = accountRole ? accountRole.value : 'user';
    const adminCode = adminCodeInput ? adminCodeInput.value.trim() : '';
    const rememberMe = document.getElementById('remember').checked;

    // Validate
    let hasError = false;

    if (!validateEmail(email)) {
      document.getElementById('email-error').textContent = 'Email tidak valid';
      hasError = true;
    }

    if (!validatePassword(password)) {
      document.getElementById('password-error').textContent = 'Password minimal 6 karakter';
      hasError = true;
    }

    if (selectedRole === 'admin' && adminCode === '') {
      const adminCodeError = document.getElementById('admin-code-error');
      if (adminCodeError) adminCodeError.textContent = 'Kode admin wajib diisi';
      hasError = true;
    }

    if (hasError) {
      showAlert('Mohon periksa kembali form Anda', 'error');
      return;
    }

    // Show loading state
    const loginBtn = document.querySelector('.btn-login');
    loginBtn.disabled = true;
    loginBtn.classList.add('loading');

    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, account_role: selectedRole, admin_code: adminCode, verification_code: verificationCode, rememberMe }),
      });

      const data = await response.json();

      if (response.ok) {
        showAlert('Login berhasil! Mengalihkan...', 'success');
        setTimeout(() => {
          window.location.href = '/';
        }, 1500);
      } else {
        showAlert(data.message || 'Login gagal', 'error');
      }
    } catch (error) {
      console.error('Login error:', error);
      showAlert('Terjadi kesalahan. Coba lagi nanti.', 'error');
    } finally {
      loginBtn.disabled = false;
      loginBtn.classList.remove('loading');
    }
  });
}

// Initialize Google Sign In
function initializeGoogleSignIn() {
  // Check if Google library is loaded
  if (typeof google === 'undefined' || !google.accounts || !google.accounts.id) {
    // Retry after Google library loads
    setTimeout(initializeGoogleSignIn, 100);
    return;
  }

  const GOOGLE_CLIENT_ID = '283549149547-j1q3h3kritseoalm93656gbhggg48eeh.apps.googleusercontent.com';
  
  // Initialize Google Sign In
  google.accounts.id.initialize({
    client_id: GOOGLE_CLIENT_ID,
    callback: handleGoogleSignInResponse,
  });

  // Show the Google button via native Google library
  google.accounts.id.renderButton(
    document.getElementById('google-signin-btn'),
    {
      type: 'standard',
      size: 'large',
      text: 'signin_with',
      theme: 'outline',
      logo_alignment: 'left',
    }
  );

  google.accounts.id.prompt();
}

function findGoogleSigninButton() {
  return document.getElementById('google-signin-btn') || document.querySelector('#google-signin-container button');
}

async function handleGoogleSignInResponse(response) {
  const credential = response.credential;

  if (!credential) {
    showAlert('Gagal mendapatkan credential dari Google', 'error');
    return;
  }

  const googleSignInBtn = findGoogleSigninButton();
  const originalText = googleSignInBtn ? googleSignInBtn.textContent : '';
  if (googleSignInBtn) {
    googleSignInBtn.disabled = true;
    googleSignInBtn.textContent = 'Loading...';
  }

  try {
    const response = await fetch('/api/login/google', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ credential }),
    });

    const data = await response.json();

    if (response.ok) {
      showAlert('Login dengan Google berhasil! Mengalihkan...', 'success');
      setTimeout(() => {
        window.location.href = '/';
      }, 1500);
    } else {
      showAlert(data.message || 'Login dengan Google gagal', 'error');
      if (googleSignInBtn) {
        googleSignInBtn.disabled = false;
        googleSignInBtn.textContent = originalText;
      }
    }
  } catch (error) {
    console.error('Google login error:', error);
    showAlert('Terjadi kesalahan saat login dengan Google', 'error');
    if (googleSignInBtn) {
      googleSignInBtn.disabled = false;
      googleSignInBtn.textContent = originalText;
    }
  }
}

// Check if already logged in
async function checkAuthStatus() {
  try {
    const response = await fetch('/api/auth/status');
    const data = await response.json();
    
    if (data.authenticated) {
      window.location.href = '/dashboard';
    }
  } catch (error) {
    console.error('Auth status check error:', error);
  }
}

// Check auth status on page load
document.addEventListener('DOMContentLoaded', () => {
  checkAuthStatus();
  initializeGoogleSignIn();
});
