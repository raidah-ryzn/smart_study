const signupRole = document.getElementById('signup-role');
const signupAdminCodeGroup = document.getElementById('signup-admin-code-group');
const signupAdminCode = document.getElementById('signup-admin-code');

function updateSignupRoleFields() {
  const isAdmin = signupRole && signupRole.value === 'admin';
  if (signupAdminCodeGroup) signupAdminCodeGroup.classList.toggle('hidden', !isAdmin);
  if (signupAdminCode) signupAdminCode.required = Boolean(isAdmin);
}

function toggleSignupPassword(event) {
  event.preventDefault();
  const input = document.getElementById('signup-password');
  input.type = input.type === 'password' ? 'text' : 'password';
}

function toggleSignupPasswordConfirm(event) {
  event.preventDefault();
  const input = document.getElementById('signup-password-confirm');
  input.type = input.type === 'password' ? 'text' : 'password';
}

function showSignupAlert(message, type = 'error') {
  const alert = document.getElementById('signup-alert-message');
  alert.textContent = message;
  alert.className = `alert ${type}`;
  alert.style.display = 'block';
}

if (signupRole) {
  signupRole.addEventListener('change', updateSignupRoleFields);
  updateSignupRoleFields();
}

document.getElementById('signup-form')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const name = document.getElementById('signup-name').value.trim();
  const email = document.getElementById('signup-email').value.trim();
  const password = document.getElementById('signup-password').value;
  const passwordConfirm = document.getElementById('signup-password-confirm').value;
  const accountRole = signupRole ? signupRole.value : 'user';
  const adminCode = signupAdminCode ? signupAdminCode.value.trim() : '';

  if (password !== passwordConfirm) {
    showSignupAlert('Password tidak cocok');
    return;
  }
  if (accountRole === 'admin' && !adminCode) {
    document.getElementById('signup-admin-code-error').textContent = 'Kode admin wajib diisi';
    showSignupAlert('Mohon isi kode admin');
    return;
  }

  const button = document.querySelector('#signup-form .btn-login');
  button.disabled = true;
  try {
    const response = await fetch('/api/register', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        name,
        email,
        password,
        password_confirm: passwordConfirm,
        account_role: accountRole,
        admin_code: adminCode
      })
    });
    const data = await response.json();
    if (!response.ok) {
      showSignupAlert(data.message || 'Registrasi gagal');
      return;
    }
    showSignupAlert(data.message, 'success');
    setTimeout(() => { window.location.href = '/login'; }, 1200);
  } catch (error) {
    console.error('Signup error:', error);
    showSignupAlert('Terjadi kesalahan. Coba lagi nanti.');
  } finally {
    button.disabled = false;
  }
});