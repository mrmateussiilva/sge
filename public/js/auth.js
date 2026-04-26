/* js/auth.js */
const isLocalAuth = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
const AUTH_API_BASE_URL = isLocalAuth ? "http://127.0.0.1:8000/api" : "/api";
const TOKEN_STORAGE_KEY = "sge_access_token";
const USER_STORAGE_KEY = "sge_usuario";

function liberarRenderAuth() {
  document.documentElement.classList.remove("auth-pending");
}

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
    window.location.replace("/login");
  }
}

async function login(email, senha) {
  const response = await fetch(`${AUTH_API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, senha }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Não foi possível fazer login.");
  }

  salvarToken(data.access_token);
  salvarUsuario(data.usuario);
  return data;
}

function protegerPagina() {
  if (!obterToken()) {
    window.location.replace("/login");
    return false;
  }

  preencherUsuario();

  document.querySelectorAll("[data-logout]").forEach((element) => {
    element.addEventListener("click", () => logout());
  });
  liberarRenderAuth();
  return true;
}

function redirecionarSeAutenticado() {
  if (!obterToken()) {
    liberarRenderAuth();
    return;
  }
  window.location.replace("/");
}
