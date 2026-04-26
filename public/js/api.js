const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
const API_BASE_URL = window.SGE_CONFIG?.API_BASE_URL || (isLocal ? "http://127.0.0.1:8000/api" : "/api");

async function request(path, options = {}) {
  const token = window.obterToken ? obterToken() : null;
  let response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
      ...options,
    });
  } catch (error) {
    throw new Error("Não foi possível conectar com a API. Verifique a URL configurada e a disponibilidade do serviço.");
  }

  if (response.status === 401) {
    if (window.logout) {
      logout(false);
    }
    window.location.replace(getLoginUrl());
    throw new Error("Sessão expirada. Faça login novamente.");
  }

  if (!response.ok) {
    let message = "Erro ao comunicar com a API.";
    try {
      const errorData = await response.json();
      message = errorData.detail || message;
    } catch (error) {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

window.api = {
  getProdutos: () => request("/produtos"),
  getProduto: (id) => request(`/produtos/${id}`),
  createProduto: (payload) => request("/produtos", { method: "POST", body: JSON.stringify(payload) }),
  updateProduto: (id, payload) => request(`/produtos/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteProduto: (id) => request(`/produtos/${id}`, { method: "DELETE" }),
  getMovimentacoes: () => request("/movimentacoes"),
  createMovimentacao: (payload) => request("/movimentacoes", { method: "POST", body: JSON.stringify(payload) }),
  getDashboard: () => request("/dashboard"),
  getUsuarios: () => request("/usuarios"),
  createUsuario: (payload) => request("/usuarios", { method: "POST", body: JSON.stringify(payload) }),
  updateUsuario: (id, payload) => request(`/usuarios/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  previewXml: async (file) => {
    const fd = new FormData();
    fd.append("file", file);
    const token = window.obterToken ? window.obterToken() : null;
    let res;
    try {
      res = await fetch(`${API_BASE_URL}/importacao/xml/preview`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: fd
      });
    } catch (error) {
      throw new Error("Falha ao enviar o XML para análise. Confirme se a API está acessível.");
    }
    if (!res.ok) {
      let errStr = "Falha ao processar arquivo XML";
      try { errStr = (await res.json()).detail || errStr } catch (e) { }
      throw new Error(errStr);
    }
    return res.json();
  },
  confirmarImportacaoXml: (payload) => request("/importacao/xml/confirmar", { method: "POST", body: JSON.stringify(payload) }),
  getHealth: () => request("/health"),
  getDbHealth: () => request("/health/db")
};
