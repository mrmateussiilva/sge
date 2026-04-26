const dashboardMovimentacoes = document.getElementById("dashboardMovimentacoes");
const alertasEstoque = document.getElementById("alertasEstoque");

function formatarData(valor) {
  return new Date(valor).toLocaleString("pt-BR");
}

function badgeTipo(tipo) {
  const classes = {
    entrada: "badge-entrada",
    saida: "badge-saida",
    ajuste: "badge-ajuste",
  };

  const icons = {
    entrada: "bi-arrow-down-circle",
    saida: "bi-arrow-up-circle",
    ajuste: "bi-sliders",
  };

  return `
    <span class="custom-badge ${classes[tipo] || "badge-ajuste"}">
      <i class="bi ${icons[tipo] || "bi-circle"}"></i>
      ${tipo}
    </span>
  `;
}

function renderEmptyMovimentacoes(titulo, texto, icone = "bi-inbox") {
  dashboardMovimentacoes.innerHTML = `
    <tr>
      <td colspan="5">
        <div class="empty-state compact-empty">
          <div class="empty-state-icon">
            <i class="bi ${icone}"></i>
          </div>
          <div>
            <div class="empty-state-title">${titulo}</div>
            <div class="empty-state-text">${texto}</div>
          </div>
        </div>
      </td>
    </tr>
  `;
}

function renderEmptyAlertas(titulo, texto, icone = "bi-shield-check") {
  alertasEstoque.innerHTML = `
    <div class="empty-state">
      <div class="empty-state-icon">
        <i class="bi ${icone}"></i>
      </div>
      <div class="empty-state-title">${titulo}</div>
      <div class="empty-state-text">${texto}</div>
    </div>
  `;
}

function renderMovimentacoes(movimentacoes) {
  if (!movimentacoes.length) {
    renderEmptyMovimentacoes(
      "Nenhuma movimentacao encontrada",
      "As entradas, saidas e ajustes aparecerao aqui assim que forem registrados.",
      "bi-journal-x",
    );
    return;
  }

  dashboardMovimentacoes.innerHTML = movimentacoes
    .map(
      (movimentacao) => `
        <tr>
          <td>
            <div class="produto-cell">
              <span class="produto-cell-title">${movimentacao.produto.nome}</span>
              <span class="produto-cell-subtitle">SKU ${movimentacao.produto.sku}</span>
            </div>
          </td>
          <td>${badgeTipo(movimentacao.tipo)}</td>
          <td>${movimentacao.quantidade}</td>
          <td>${movimentacao.motivo || "-"}</td>
          <td>${formatarData(movimentacao.created_at)}</td>
        </tr>
      `,
    )
    .join("");
}

function renderAlertas(produtosBaixos, produtosZerados) {
  if (!produtosBaixos.length) {
    renderEmptyAlertas(
      "Nenhum alerta no momento",
      "Todos os produtos estao acima do estoque minimo configurado.",
      "bi-check2-circle",
    );
    return;
  }

  const prioridades = [...produtosBaixos].sort((a, b) => a.estoque_atual - b.estoque_atual);

  alertasEstoque.innerHTML = prioridades
    .slice(0, 6)
    .map((produto) => {
      const zerado = produto.estoque_atual === 0;
      const classe = zerado ? "alert-item-danger" : "alert-item-warning";
      const icone = zerado ? "bi-x-octagon" : "bi-exclamation-circle";
      const mensagem = zerado
        ? "Sem estoque disponivel. Reposicao recomendada com prioridade."
        : `Abaixo do minimo configurado (${produto.estoque_minimo} ${produto.unidade}).`;

      return `
        <article class="alert-item ${classe}">
          <div class="alert-item-icon">
            <i class="bi ${icone}"></i>
          </div>
          <div>
            <h4 class="alert-item-title">${produto.nome}</h4>
            <p class="alert-item-text">${mensagem}</p>
            <span class="alert-item-meta">
              SKU ${produto.sku} • Atual: ${produto.estoque_atual} ${produto.unidade}
            </span>
          </div>
        </article>
      `;
    })
    .join("");

  document.getElementById("estoqueZerado").textContent = produtosZerados.length;
}

async function carregarDashboard() {
  try {
    const [dashboard, produtos] = await Promise.all([api.getDashboard(), api.getProdutos()]);
    const produtosZerados = produtos.filter((produto) => produto.estoque_atual === 0);

    document.getElementById("totalProdutos").textContent = dashboard.total_produtos;
    document.getElementById("estoqueBaixo").textContent = dashboard.produtos_com_estoque_baixo.length;
    document.getElementById("estoqueZerado").textContent = produtosZerados.length;
    document.getElementById("totalMovimentacoes").textContent = dashboard.ultimas_movimentacoes.length;

    renderMovimentacoes(dashboard.ultimas_movimentacoes);
    renderAlertas(dashboard.produtos_com_estoque_baixo, produtosZerados);
  } catch (error) {
    renderEmptyMovimentacoes(
      "Nao foi possivel carregar o painel",
      error.message,
      "bi-wifi-off",
    );
    renderEmptyAlertas(
      "Falha ao buscar alertas",
      "Confira se a API esta em execucao e tente novamente.",
      "bi-exclamation-diamond",
    );
  }
}

carregarDashboard();
