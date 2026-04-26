const produtoSelect = document.getElementById("produto_id");
const tipoInput = document.getElementById("tipo");
const movimentacaoForm = document.getElementById("movimentacaoForm");
const movimentacaoErro = document.getElementById("movimentacaoErro");
const movimentacoesTabela = document.getElementById("movimentacoesTabela");
const segmentButtons = document.querySelectorAll(".segment-button");

function formatarData(valor) {
  return new Date(valor).toLocaleString("pt-BR");
}

function badgeTipo(tipo) {
  const classes = {
    entrada: "type-entrada",
    saida: "type-saida",
    ajuste: "type-ajuste",
  };

  return `<span class="type-badge ${classes[tipo] || "type-ajuste"}">${tipo}</span>`;
}

function renderEmptyMovimentacoes(title, text, icon = "bi-inbox") {
  movimentacoesTabela.innerHTML = `
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

async function carregarProdutosSelect() {
  const produtos = await api.getProdutos();
  produtoSelect.innerHTML =
    '<option value="">Selecione um produto</option>' +
    produtos.map((produto) => `<option value="${produto.id}">${produto.nome} (${produto.sku})</option>`).join("");
}

async function carregarMovimentacoes() {
  try {
    const movimentacoes = await api.getMovimentacoes();

    if (!movimentacoes.length) {
      renderEmptyMovimentacoes(
        "Nenhuma movimentacao registrada",
        "As entradas, saidas e ajustes aparecerao aqui.",
        "bi-journal-x",
      );
      return;
    }

    movimentacoesTabela.innerHTML = movimentacoes
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
  } catch (error) {
    renderEmptyMovimentacoes("Falha ao carregar historico", error.message, "bi-wifi-off");
  }
}

segmentButtons.forEach((button) => {
  button.addEventListener("click", () => {
    segmentButtons.forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    tipoInput.value = button.dataset.tipo;
  });
});

movimentacaoForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  movimentacaoErro.classList.add("d-none");

  const payload = {
    produto_id: Number(produtoSelect.value),
    tipo: tipoInput.value,
    quantidade: Number(document.getElementById("quantidade").value),
    motivo: document.getElementById("motivo").value.trim() || null,
  };

  try {
    await api.createMovimentacao(payload);
    movimentacaoForm.reset();
    tipoInput.value = "entrada";
    segmentButtons.forEach((button) => button.classList.toggle("active", button.dataset.tipo === "entrada"));
    await carregarProdutosSelect();
    await carregarMovimentacoes();
  } catch (error) {
    movimentacaoErro.textContent = error.message;
    movimentacaoErro.classList.remove("d-none");
  }
});

async function inicializarPagina() {
  try {
    await carregarProdutosSelect();
    await carregarMovimentacoes();
  } catch (error) {
    movimentacaoErro.textContent = error.message;
    movimentacaoErro.classList.remove("d-none");
  }
}

inicializarPagina();
