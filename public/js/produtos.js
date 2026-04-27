const produtoModalEl = document.getElementById("produtoModal");
const produtoModal = new bootstrap.Modal(produtoModalEl);

let produtosCache = [];
let editingProdutoId = null;

const produtosTabela = document.getElementById("produtosTabela");
const produtoForm = document.getElementById("produtoForm");
const produtoErro = document.getElementById("produtoErro");
const produtoTitulo = document.getElementById("produtoModalLabel");
const buscaProduto = document.getElementById("buscaProduto");
const filtroStatus = document.getElementById("filtroStatus");
const filtroCategoria = document.getElementById("filtroCategoria");
const contadorProdutos = document.getElementById("contadorProdutos");

function getStatusProduto(produto) {
  if (produto.estoque_atual === 0) {
    return { key: "zerado", label: "Zerado", className: "status-zero" };
  }

  if (produto.estoque_atual <= produto.estoque_minimo) {
    return { key: "baixo", label: "Baixo", className: "status-low" };
  }

  return { key: "ok", label: "OK", className: "status-ok" };
}

function popularCategorias(produtos) {
  const categorias = [...new Set(produtos.map((produto) => produto.categoria).filter(Boolean))].sort();
  filtroCategoria.innerHTML =
    '<option value="todas">Todas as categorias</option>' +
    categorias.map((categoria) => `<option value="${categoria}">${categoria}</option>`).join("");
}

function renderEmptyProdutos(title, text, icon = "bi-inbox") {
  produtosTabela.innerHTML = `
    <tr>
      <td colspan="7">
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

function aplicarFiltros() {
  const termo = buscaProduto.value.trim().toLowerCase();
  const status = filtroStatus.value;
  const categoria = filtroCategoria.value;

  const filtrados = produtosCache.filter((produto) => {
    const matchTermo =
      !termo ||
      produto.nome.toLowerCase().includes(termo) ||
      produto.sku.toLowerCase().includes(termo);

    const statusProduto = getStatusProduto(produto).key;
    const matchStatus = status === "todos" || statusProduto === status;
    const matchCategoria =
      categoria === "todas" || (produto.categoria || "Sem categoria") === categoria;

    return matchTermo && matchStatus && matchCategoria;
  });

  contadorProdutos.textContent = `${filtrados.length} item${filtrados.length === 1 ? "" : "s"}`;

  if (!filtrados.length) {
    renderEmptyProdutos(
      "Nenhum produto encontrado",
      "Ajuste os filtros ou cadastre um novo item para o estoque.",
      "bi-search",
    );
    return;
  }

  produtosTabela.innerHTML = filtrados
    .map((produto) => {
      const statusProduto = getStatusProduto(produto);
      return `
        <tr>
          <td>
            <div class="item-main">
              <span class="item-title">${produto.nome}</span>
              <span class="item-subtitle">${produto.localizacao || produto.unidade}</span>
            </div>
          </td>
          <td>${produto.sku}</td>
          <td>${produto.categoria || "Sem categoria"}</td>
          <td class="stock-inline">${produto.estoque_atual} ${produto.unidade}</td>
          <td>${produto.estoque_minimo}</td>
          <td><span class="status-badge ${statusProduto.className}">${statusProduto.label}</span></td>
          <td>
            <div class="action-buttons">
              <button class="icon-button" type="button" title="Editar produto" data-edit-id="${produto.id}">
                <i class="bi bi-pencil"></i>
              </button>
              <a class="icon-button" href="movimentacoes.html" title="Nova movimentacao">
                <i class="bi bi-arrow-left-right"></i>
              </a>
              <button class="icon-button icon-button-danger" type="button" title="Excluir produto" data-delete-id="${produto.id}">
                <i class="bi bi-trash3"></i>
              </button>
            </div>
          </td>
        </tr>
      `;
    })
    .join("");
}

async function carregarProdutos() {
  try {
    produtosCache = await api.getProdutos();
    popularCategorias(produtosCache);

    if (!produtosCache.length) {
      contadorProdutos.textContent = "0 itens";
      renderEmptyProdutos(
        "Nenhum produto cadastrado",
        "Use o botao Adicionar produto para comecar.",
        "bi-box2",
      );
      return;
    }

    aplicarFiltros();
  } catch (error) {
    renderEmptyProdutos("Falha ao carregar produtos", error.message, "bi-wifi-off");
  }
}

function abrirFormulario(produto = null) {
  editingProdutoId = produto?.id || null;
  produtoForm.reset();
  produtoErro.classList.add("d-none");

  if (produto) {
    produtoTitulo.textContent = "Editar produto";
    document.getElementById("nome").value = produto.nome || "";
    document.getElementById("sku").value = produto.sku || "";
    document.getElementById("categoria").value = produto.categoria || "";
    document.getElementById("unidade").value = produto.unidade || "";
    document.getElementById("custo").value = produto.custo || "";
    document.getElementById("preco").value = produto.preco || "";
    document.getElementById("estoque_atual").value = produto.estoque_atual || "";
    document.getElementById("estoque_minimo").value = produto.estoque_minimo || "";
    document.getElementById("localizacao").value = produto.localizacao || "";
  } else {
    produtoTitulo.textContent = "Novo produto";
  }

  produtoModal.show();
}

function inicializarFormulario() {
  const novoBtn = document.getElementById("novoProdutoBtn");
  if (novoBtn) {
    novoBtn.addEventListener("click", () => abrirFormulario());
  }
}

produtoForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  produtoErro.classList.add("d-none");

  const payload = {
    nome: document.getElementById("nome").value.trim(),
    sku: document.getElementById("sku").value.trim(),
    categoria: document.getElementById("categoria").value.trim() || null,
    unidade: document.getElementById("unidade").value.trim(),
    custo: Number(document.getElementById("custo").value),
    preco: Number(document.getElementById("preco").value),
    estoque_atual: Number(document.getElementById("estoque_atual").value),
    estoque_minimo: Number(document.getElementById("estoque_minimo").value),
    localizacao: document.getElementById("localizacao").value.trim() || null,
  };

  try {
    if (editingProdutoId) {
      await api.updateProduto(editingProdutoId, payload);
    } else {
      await api.createProduto(payload);
    }
    produtoForm.reset();
    produtoModal.hide();
    await carregarProdutos();
  } catch (error) {
    produtoErro.textContent = error.message;
    produtoErro.classList.remove("d-none");
  }
});

produtosTabela.addEventListener("click", async (event) => {
  const editButton = event.target.closest("[data-edit-id]");
  if (editButton) {
    const id = Number(editButton.dataset.editId);
    const produto = produtosCache.find((p) => p.id === id);
    if (produto) {
      abrirFormulario(produto);
    }
    return;
  }

  const button = event.target.closest("[data-delete-id]");
  if (!button) {
    return;
  }

  const { deleteId } = button.dataset;
  if (!window.confirm("Excluir este produto?")) {
    return;
  }

  try {
    await api.deleteProduto(deleteId);
    await carregarProdutos();
  } catch (error) {
    window.alert(error.message);
  }
});

buscaProduto.addEventListener("input", aplicarFiltros);
filtroStatus.addEventListener("change", aplicarFiltros);
filtroCategoria.addEventListener("change", aplicarFiltros);

inicializarFormulario();
carregarProdutos();
