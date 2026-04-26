const AUTH_API_BASE_URL = "http://127.0.0.1:8000";
const TOKEN_STORAGE_KEY = "sge_access_token";
const USER_STORAGE_KEY = "sge_usuario";

function salvarToken(token) {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

function salvarUsuario(usuario) {
  localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(usuario));
}

function obterToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

function usuarioAtual() {
  const raw = localStorage.getItem(USER_STORAGE_KEY);
  return raw ? JSON.parse(raw) : null;
}

function preencherUsuario() {
  const usuario = usuarioAtual();
  document.querySelectorAll("[data-usuario-nome]").forEach((element) => {
    element.textContent = usuario?.nome || "Operador";
  });
}

function logout(redirecionar = true) {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
  localStorage.removeItem(USER_STORAGE_KEY);

  if (redirecionar) {
    window.location.href = "login.html";
  }
}

async function login(email, senha) {
  const response = await fetch(`${AUTH_API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, senha }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Nao foi possivel fazer login.");
  }

  salvarToken(data.access_token);
  salvarUsuario(data.usuario);
  return data;
}

function protegerPagina() {
  if (!obterToken()) {
    window.location.href = "login.html";
    return;
  }

  preencherUsuario();

  document.querySelectorAll("[data-logout]").forEach((element) => {
    element.addEventListener("click", () => logout());
  });
}

function redirecionarSeAutenticado() {
  if (obterToken()) {
    window.location.href = "index.html";
  }
}
