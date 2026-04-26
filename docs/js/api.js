const API_BASE_URL = "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const token = window.obterToken ? obterToken() : null;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  if (response.status === 401) {
    if (window.logout) {
      logout(false);
    }
    window.location.href = "login.html";
    throw new Error("Sessao expirada. Faca login novamente.");
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

const api = {
  getMe() {
    return request("/auth/me");
  },
  getProdutos() {
    return request("/produtos");
  },
  getProduto(id) {
    return request(`/produtos/${id}`);
  },
  createProduto(payload) {
    return request("/produtos", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  deleteProduto(id) {
    return request(`/produtos/${id}`, {
      method: "DELETE",
    });
  },
  getMovimentacoes() {
    return request("/movimentacoes");
  },
  createMovimentacao(payload) {
    return request("/movimentacoes", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getDashboard() {
    return request("/dashboard");
  },
};
