const API_BASE_URL = "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

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
