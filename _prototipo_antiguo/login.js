const form = document.getElementById('form-login');
const errorBox = document.getElementById('error');

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  errorBox.style.display = 'none';

  const correo = document.getElementById('correo').value;
  const password = document.getElementById('clave').value;

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ correo, password })
    });

    const data = await res.json();
    if (!data.ok) throw new Error(data.error || 'Credenciales inválidas');

    sessionStorage.setItem('usuario_quero', JSON.stringify(data.usuario));
    window.location.href = '/panel.html';
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.style.display = 'block';
  }
});