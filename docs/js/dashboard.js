const dashboardMovimentacoes = document.getElementById("dashboardMovimentacoes");
const alertasEstoque = document.getElementById("alertasEstoque");

function formatarData(valor) {
  return new Date(valor).toLocaleString("pt-BR");
}

function badgeTipo(tipo) {
  const classes = {
    entrada: "type-entrada",
    saida: "type-saida",
    ajuste: "type-ajuste",
  };

  const icons = {
    entrada: "bi-arrow-down-circle",
    saida: "bi-arrow-up-circle",
    ajuste: "bi-sliders",
  };

  return `<span class="type-badge ${classes[tipo] || "type-ajuste"}"><i class="bi ${icons[tipo] || "bi-circle"}"></i>${tipo}</span>`;
}

function renderEmptyMovimentacoes(title, text, icon) {
  dashboardMovimentacoes.innerHTML = `
    <tr>
      <td colspan="5">
        <div class="empty-state empty-state-inline">
          <div class="empty-state-icon"><i class="bi ${icon}"></i></div>
          <div>
            <div class="empty-state-title">${title}</div>
            <div class="empty-state-text">${text}</div>
          </div>
        </div>
      </td>
    </tr>
  `;
}

function renderAlertas(produtosBaixos) {
  if (!produtosBaixos.length) {
    alertasEstoque.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon"><i class="bi bi-check2-circle"></i></div>
        <div class="empty-state-title">Nenhum alerta no momento</div>
        <div class="empty-state-text">Todos os produtos estao acima do minimo configurado.</div>
      </div>
    `;
    return;
  }

  alertasEstoque.innerHTML = produtosBaixos
    .sort((a, b) => a.estoque_atual - b.estoque_atual)
    .slice(0, 6)
    .map((produto) => {
      const zerado = produto.estoque_atual === 0;
      return `
        <article class="alert-row ${zerado ? "alert-row-zero" : "alert-row-low"}">
          <div class="alert-icon">
            <i class="bi ${zerado ? "bi-x-octagon" : "bi-exclamation-triangle"}"></i>
          </div>
          <div>
            <h3 class="alert-title">${produto.nome}</h3>
            <p class="alert-text">${zerado ? "Estoque zerado." : "Abaixo do minimo configurado."}</p>
            <p class="alert-meta">SKU ${produto.sku} • Atual ${produto.estoque_atual} ${produto.unidade}</p>
          </div>
        </article>
      `;
    })
    .join("");
}

async function carregarDashboard() {
  try {
    const [dashboard, produtos] = await Promise.all([api.getDashboard(), api.getProdutos()]);
    const produtosZerados = produtos.filter((produto) => produto.estoque_atual === 0);

    document.getElementById("totalProdutos").textContent = dashboard.total_produtos;
    document.getElementById("estoqueBaixo").textContent = dashboard.produtos_com_estoque_baixo.length;
    document.getElementById("estoqueZerado").textContent = produtosZerados.length;
    document.getElementById("totalMovimentacoes").textContent = dashboard.ultimas_movimentacoes.length;

    if (!dashboard.ultimas_movimentacoes.length) {
      renderEmptyMovimentacoes(
        "Nenhuma movimentacao encontrada",
        "Os novos lancamentos aparecerao aqui.",
        "bi-journal-x",
      );
    } else {
      dashboardMovimentacoes.innerHTML = dashboard.ultimas_movimentacoes
        .map(
          (movimentacao) => `
            <tr>
              <td>
                <div class="item-main">
                  <span class="item-title">${movimentacao.produto.nome}</span>
                  <span class="item-subtitle">SKU ${movimentacao.produto.sku}</span>
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

    renderAlertas(dashboard.produtos_com_estoque_baixo);
  } catch (error) {
    renderEmptyMovimentacoes("Falha ao carregar", error.message, "bi-wifi-off");
    alertasEstoque.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon"><i class="bi bi-exclamation-diamond"></i></div>
        <div class="empty-state-title">Falha ao buscar alertas</div>
        <div class="empty-state-text">Confira se a API esta em execucao.</div>
      </div>
    `;
  }
}

carregarDashboard();
