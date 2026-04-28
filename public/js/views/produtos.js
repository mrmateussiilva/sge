/* js/views/produtos.js */
function isLightColor(hex) {
  const h = hex?.replace('#', '') || '';
  if (h.length !== 6) return true;
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return (r * 299 + g * 587 + b * 114) / 1000 > 150;
}

window.renderProdutos = async function () {
  const appContent = document.getElementById("app-content");
  const appModals = document.getElementById("app-modals");

  appModals.innerHTML = `
    <div class="modal fade" id="produtoModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg modal-dialog-centered">
        <div class="modal-content border-0 shadow-lg">
          <div class="modal-header border-bottom py-3">
            <h5 class="modal-title fw-bold" id="produtoModalLabel">Novo produto</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
          </div>
          <div class="modal-body py-4">
            <form id="produtoForm" class="row g-3" novalidate>
              <input type="hidden" id="produtoId">
              <div class="col-md-6">
                <label for="nome" class="form-label small fw-medium">Nome *</label>
                <div class="input-group has-validation">
                  <input type="text" class="form-control" id="nome" required maxlength="150" minlength="1" placeholder="Nome do produto">
                  <div class="invalid-feedback">Nome é obrigatório</div>
                </div>
              </div>
              <div class="col-md-6">
                <label for="sku" class="form-label small fw-medium">SKU / Código *</label>
                <div class="input-group has-validation">
                  <input type="text" class="form-control" id="sku" required maxlength="80" placeholder="Código único" style="text-transform: uppercase;">
                  <div class="invalid-feedback">SKU é obrigatório</div>
                </div>
              </div>
              <div class="col-md-6">
                <label for="categoria" class="form-label small fw-medium">Categoria</label>
                <select class="form-select" id="categoria">
                  <option value="">Nenhuma</option>
                </select>
              </div>
              <div class="col-md-6">
                <label for="tag" class="form-label small fw-medium">Tag</label>
                <select class="form-select" id="tag">
                  <option value="">Nenhuma</option>
                </select>
              </div>
              <div class="col-md-4">
                <label for="unidade" class="form-label small fw-medium">Unidade *</label>
                <div class="input-group has-validation">
                  <input type="text" class="form-control" id="unidade" required maxlength="30" placeholder="UN, KG, MT" style="text-transform: uppercase;">
                  <div class="invalid-feedback">Unidade é obrigatória</div>
                </div>
              </div>
              <div class="col-md-4">
                <label for="localizacao" class="form-label small fw-medium">Localização</label>
                <input type="text" class="form-control" id="localizacao" maxlength="100" placeholder="Ex: Prateleira A-1">
              </div>
              <div class="col-12">
                <div class="card bg-light border-0 py-2 px-3">
                  <span class="small fw-medium text-secondary mb-2">Valores</span>
                  <div class="row g-3">
                    <div class="col-md-4">
                      <label for="custo" class="form-label small fw-medium">Custo *</label>
                      <div class="input-group has-validation">
                        <span class="input-group-text bg-white border-end-0">R$</span>
                        <input type="text" class="form-control border-start-0" id="custo" required min="0" placeholder="0,00">
                        <div class="invalid-feedback">Custo inválido</div>
                      </div>
                    </div>
                    <div class="col-md-4">
                      <label for="preco" class="form-label small fw-medium">Preço *</label>
                      <div class="input-group has-validation">
                        <span class="input-group-text bg-white border-end-0">R$</span>
                        <input type="text" class="form-control border-start-0" id="preco" required min="0" placeholder="0,00">
                        <div class="invalid-feedback">Preço inválido</div>
                      </div>
                    </div>
                    <div class="col-md-4">
                      <label for="margem" class="form-label small fw-medium">Margem</label>
                      <div class="input-group">
                        <input type="text" class="form-control bg-light border-0" id="margem" readonly placeholder="--">
                        <span class="input-group-text bg-light border-0">%</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <label for="estoque_atual" class="form-label small fw-medium">Estoque Atual *</label>
                <div class="input-group has-validation">
                  <input type="number" class="form-control" id="estoque_atual" required min="0" step="1" placeholder="0">
                  <div class="invalid-feedback">Estoque inválido</div>
                </div>
              </div>
              <div class="col-md-6">
                <label for="estoque_minimo" class="form-label small fw-medium">Estoque Mínimo *</label>
                <div class="input-group has-validation">
                  <input type="number" class="form-control" id="estoque_minimo" required min="0" step="1" placeholder="0">
                  <div class="invalid-feedback">Estoque mínimo inválido</div>
                </div>
              </div>
              <div class="col-12">
                <div id="produtoErro" class="alert alert-danger py-2 mb-0 d-none small"></div>
              </div>
            </form>
          </div>
          <div class="modal-footer border-top py-3">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
            <button type="submit" form="produtoForm" class="btn btn-primary px-4">
              <i class="bi bi-check2 me-1"></i> Salvar
            </button>
          </div>
        </div>
      </div>
    </div>
  `;

  appContent.innerHTML = `
    <!-- Minimal Header -->
    <header class="mb-3">
      <h1 class="page-title fs-4 fw-bold mb-0 text-dark">Produtos</h1>
      <p class="text-secondary small mb-0 mt-1">Cadastro e gestão de itens operacionais</p>
    </header>

    <!-- Toolbar -->
    <div class="card-enterprise bg-white shadow-sm border-0 mb-3 d-flex flex-wrap flex-xl-nowrap align-items-center" style="padding: 14px 16px; gap: 10px;">
      
      <!-- Search -->
      <div class="input-group flex-grow-1" style="flex-basis: 300px; height: var(--input-height);">
        <span class="input-group-text bg-white text-muted border-end-0 ps-3"><i class="bi bi-search"></i></span>
        <input type="text" class="form-control bg-white border-start-0 ps-1 shadow-none h-100" placeholder="Buscar produto por nome ou SKU..." id="buscaProduto">
        <button class="btn btn-outline-secondary border bg-light text-dark px-3 fw-medium z-0 h-100" type="button" title="Buscar">Buscar</button>
      </div>
      
      <!-- Select Status -->
      <select class="form-select shadow-none bg-white flex-shrink-0" id="filtroStatus" style="width: 180px; height: var(--input-height);">
        <option value="">Status: Todos</option>
        <option value="ok">Estoque Normal</option>
        <option value="low">Estoque Baixo</option>
        <option value="zero">Zerados</option>
      </select>

      <!-- Refresh -->
      <button class="btn btn-light border bg-white shadow-sm flex-shrink-0 p-0 d-flex align-items-center justify-content-center" onclick="window.renderProdutos()" title="Atualizar dados" style="width: var(--input-height); height: var(--input-height);">
        <i class="bi bi-arrow-clockwise text-dark fs-6 lh-1"></i>
      </button>

      <!-- Novo Registro -->
      <button class="btn btn-primary shadow-sm flex-shrink-0 ms-xl-auto px-3 d-flex align-items-center justify-content-center mt-2 mt-xl-0" id="novoProdutoBtn" style="height: var(--input-height);">
        <i class="bi bi-plus-lg me-2"></i> Novo Registro
      </button>

    </div>

    <!-- Category Tabs & Table Panel -->
    <div class="card-enterprise d-flex flex-column mb-3 bg-white border-0 shadow-sm">
      
      <!-- Tabs -->
      <div class="border-bottom px-3 pt-2 bg-white rounded-top">
         <ul class="nav nav-tabs category-tabs flex-nowrap overflow-x-auto border-bottom-0 pb-0" id="produtosTabs" role="tablist" style="scrollbar-width: none;">
            <li class="nav-item">
              <span class="nav-link skeleton" style="width:100px; height: 34px;"></span>
            </li>
         </ul>
      </div>

      <!-- Table Container -->
      <div class="flex-grow-1 p-0 overflow-auto bg-white" style="border-bottom-left-radius:8px; border-bottom-right-radius:8px;">
        <div class="table-responsive">
          <table class="table table-compact mb-0 border-0">
            <thead class="position-sticky top-0 shadow-sm" style="z-index: 1;">
              <tr>
                <th class="border-start-0 border-top-0 ps-4 text-dark" style="width: 35%;">Produto</th>
                <th class="border-top-0 text-dark">Código/SKU</th>
                <th class="text-end border-top-0 text-dark">Atual</th>
                <th class="text-end border-top-0 text-dark">Mínimo</th>
                <th class="border-top-0 text-center text-dark">Status</th>
                <th class="text-end border-end-0 border-top-0 pe-4 text-dark" style="min-width: 110px;">Ações</th>
              </tr>
            </thead>
            <tbody id="produtos-list">
              <tr>
                 <td colspan="6">
                    <div class="p-4">
                      <div class="skeleton w-100 mb-3" style="height: 58px;"></div>
                      <div class="skeleton w-100 mb-3" style="height: 58px;"></div>
                      <div class="skeleton w-100" style="height: 58px;"></div>
                    </div>
                 </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  try {
    const rawProdutos = await window.api.getProdutos();
    const [categorias, tags] = await Promise.all([
      window.api.getCategorias(),
      window.api.getTags()
    ]);

    const produtos = rawProdutos.map(p => {
      let cat = p.categoria?.nome || "Sem categoria";
      let tag = p.tag?.nome || null;
      return { ...p, catNorm: cat, tagNorm: tag };
    });

    const categoriesSet = new Set();
    produtos.forEach(p => categoriesSet.add(p.catNorm));
    const sortedCategories = ["Todos", ...Array.from(categoriesSet).sort()];

    let activeCategory = localStorage.getItem("sge-active-category") || "Todos";
    if (!sortedCategories.includes(activeCategory)) {
      activeCategory = "Todos";
    }

    const tabsContainer = document.getElementById("produtosTabs");
    const tbody = document.getElementById("produtos-list");
    const busca = document.getElementById("buscaProduto");
    const filtro = document.getElementById("filtroStatus");

    const categoryCountsRaw = { "Todos": produtos.length };
    produtos.forEach(p => {
      categoryCountsRaw[p.catNorm] = (categoryCountsRaw[p.catNorm] || 0) + 1;
    });

    const renderTabs = () => {
      tabsContainer.innerHTML = sortedCategories.map(cat => {
        const isActive = cat === activeCategory;
        return `
           <li class="nav-item">
             <a href="#" class="nav-link ${isActive ? 'active fw-bold' : ''} text-nowrap d-flex align-items-center gap-2" data-category="${cat}">
                ${cat} <span class="badge ${isActive ? 'bg-primary' : 'bg-secondary'} rounded-pill" style="font-size:0.65rem">${categoryCountsRaw[cat]}</span>
             </a>
           </li>
         `;
      }).join("");

      tabsContainer.querySelectorAll(".nav-link").forEach(link => {
        link.addEventListener("click", (e) => {
          e.preventDefault();
          activeCategory = e.currentTarget.getAttribute("data-category");
          localStorage.setItem("sge-active-category", activeCategory);
          renderTabs();
          applyFilters();
        });
      });
    };

    const renderTable = (lista) => {
      if (lista.length === 0) {
        const catListCount = produtos.filter(p => activeCategory === "Todos" || p.catNorm === activeCategory).length;
        if (catListCount === 0) {
          tbody.innerHTML = `<tr><td colspan="6" class="empty-state py-5"><i class="bi bi-box2 empty-icon d-block"></i><h6 class="fw-bold text-dark">Nenhum produto nesta categoria.</h6></td></tr>`;
        } else {
          tbody.innerHTML = `<tr><td colspan="6" class="empty-state py-5"><i class="bi bi-search empty-icon d-block"></i><h6 class="fw-bold text-dark">Nada encontrado</h6><p class="text-secondary small mb-0">Tente afrouxar os parâmetros da busca.</p></td></tr>`;
        }
        return;
      }

      tbody.innerHTML = lista.sort((a, b) => a.nome.localeCompare(b.nome)).map(p => {
        let badgeClass = "ok", lbl = "Estoque OK";
        if (p.estoque_atual === 0) {
          badgeClass = "zero"; lbl = "Zerado";
        } else if (p.estoque_atual <= p.estoque_minimo) {
          badgeClass = "low"; lbl = "Baixo";
        }

        const tagHtml = p.tag ? `<span class="badge rounded-pill ms-2" style="background-color: ${p.tag.cor || '#6c757d'}; color: ${isLightColor(p.tag.cor || '#6c757d') ? '#000' : '#fff'}; font-size: 0.65rem;">${window.escapeHtml(p.tag.nome)}</span>` : '';

        return `
          <tr>
            <td class="ps-4">
              <div class="d-flex flex-column justify-content-center">
                 <span class="fw-bold text-dark text-truncate" style="max-width: 300px; font-size: 0.90rem; letter-spacing: -0.01em;" title="${p.nome}">${p.nome}</span>
                 <span class="text-muted d-flex align-items-center mt-1" style="font-size: 0.75rem;">
                   <i class="bi bi-tag me-1 opacity-75"></i> ${p.catNorm}${tagHtml}
                 </span>
              </div>
            </td>
            <td><span class="badge rounded-pill border bg-white border-light-subtle text-secondary font-monospace px-2 py-1 shadow-sm" style="font-weight: 500; font-size: 0.70rem;">${p.sku}</span></td>
            <td class="text-end">
              <span class="fw-bold text-dark fs-6">${p.estoque_atual}</span> <small class="text-muted fw-medium ms-1" style="font-size:0.75rem">${p.unidade}</small>
            </td>
            <td class="text-end text-muted" style="font-weight:600;">${p.estoque_minimo}</td>
            <td class="text-center">
               <div class="badge-status ${badgeClass} shadow-sm">
                  <span class="dot"></span> ${lbl}
               </div>
            </td>
<td class="text-end pe-4">
               <div class="d-flex justify-content-end gap-2 actions-group">
                  <button class="btn border border-light-subtle text-primary p-0 d-flex align-items-center justify-content-center action-btn" style="width:32px; height:32px; border-radius: 6px;" title="Lançar Movimento" aria-label="Atalho" onclick="window.location.hash='#/movimentacoes'">
                     <i class="bi bi-arrow-down-up" style="font-size: 0.95rem"></i>
                  </button>
                  <button class="btn border border-light-subtle text-secondary p-0 d-flex align-items-center justify-content-center action-btn" style="width:32px; height:32px; border-radius: 6px;" title="Editar" data-edit-id="${p.id}">
                     <i class="bi bi-pencil" style="font-size: 0.90rem"></i>
                  </button>
                  <button class="btn border border-light-subtle text-danger p-0 d-flex align-items-center justify-content-center action-btn" style="width:32px; height:32px; border-radius: 6px;" title="Excluir" data-delete-id="${p.id}">
                     <i class="bi bi-trash3" style="font-size: 0.90rem"></i>
                  </button>
               </div>
            </td>
          </tr>
        `;
      }).join("");
    };

    const applyFilters = () => {
      const b = busca.value.toLowerCase().trim();
      const f = filtro.value;
      const res = produtos.filter(p => {
        if (activeCategory !== "Todos" && p.catNorm !== activeCategory) return false;
        const matchBusca = !b || p.nome.toLowerCase().includes(b) || p.sku.toLowerCase().includes(b);
        if (!matchBusca) return false;
        let status = "ok";
        if (p.estoque_atual === 0) status = "zero";
        else if (p.estoque_atual <= p.estoque_minimo) status = "low";
        return !f || f === status;
      });
      renderTable(res);
    };

    busca.addEventListener("input", applyFilters);
    filtro.addEventListener("change", applyFilters);

    const btnBuscar = busca.parentElement.querySelector("button");
    if (btnBuscar) btnBuscar.addEventListener("click", applyFilters);

    renderTabs();
    applyFilters();

    const produtoModal = new bootstrap.Modal(document.getElementById("produtoModal"));
    const produtoForm = document.getElementById("produtoForm");
    const produtoErro = document.getElementById("produtoErro");
    const produtoTitulo = document.getElementById("produtoModalLabel");
    let editingId = null;

    function formatCurrency(value) {
      if (!value || isNaN(value)) return "0,00";
      return parseFloat(value).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function parseCurrency(str) {
      if (!str) return 0;
      return parseFloat(str.replace(/\./g, "").replace(",", ".")) || 0;
    }

    function calculateMargem() {
      const custo = parseCurrency(document.getElementById("custo").value);
      const preco = parseCurrency(document.getElementById("preco").value);
      const margemInput = document.getElementById("margem");
      if (custo > 0 && preco > 0) {
        const margem = ((preco - custo) / custo * 100).toFixed(1);
        margemInput.value = margem + "%";
      } else {
        margemInput.value = "--";
      }
    }

    function setupCurrencyMask(input) {
      input.addEventListener("input", (e) => {
        let value = e.target.value.replace(/\D/g, "");
        if (value) {
          value = (parseInt(value) / 100).toFixed(2);
          value = value.replace(".", ",");
        }
        e.target.value = value;
      });
      input.addEventListener("blur", () => {
        calculateMargem();
      });
    }

    function abrirFormulario(produto = null) {
      editingId = produto?.id || null;
      produtoForm.reset();
      produtoErro.classList.add("d-none");
      produtoForm.classList.remove("was-validated");

      const catSelect = document.getElementById("categoria");
      const tagSelect = document.getElementById("tag");
      catSelect.innerHTML = '<option value="">Nenhuma</option>' + categorias.map(c => `<option value="${c.id}">${window.escapeHtml(c.nome)}</option>`).join("");
      tagSelect.innerHTML = '<option value="">Nenhuma</option>' + tags.map(t => `<option value="${t.id}">${window.escapeHtml(t.nome)}</option>`).join("");

      setupCurrencyMask(document.getElementById("custo"));
      setupCurrencyMask(document.getElementById("preco"));

      if (produto) {
        produtoTitulo.textContent = "Editar produto";
        document.getElementById("produtoId").value = produto.id;
        document.getElementById("nome").value = produto.nome || "";
        document.getElementById("sku").value = produto.sku || "";
        catSelect.value = produto.categoria_id || "";
        tagSelect.value = produto.tag_id || "";
        document.getElementById("unidade").value = produto.unidade || "";
        document.getElementById("custo").value = produto.custo ? formatCurrency(produto.custo) : "";
        document.getElementById("preco").value = produto.preco ? formatCurrency(produto.preco) : "";
        document.getElementById("estoque_atual").value = produto.estoque_atual || "";
        document.getElementById("estoque_minimo").value = produto.estoque_minimo || "";
        document.getElementById("localizacao").value = produto.localizacao || "";
        calculateMargem();
      } else {
        produtoTitulo.textContent = "Novo produto";
        document.getElementById("produtoId").value = "";
        document.getElementById("margem").value = "--";
      }

      produtoModal.show();
    }

    document.getElementById("novoProdutoBtn").addEventListener("click", () => abrirFormulario());

    produtoForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      produtoErro.classList.add("d-none");

      if (!produtoForm.checkValidity()) {
        produtoForm.classList.add("was-validated");
        return;
      }

      const payload = {
        nome: document.getElementById("nome").value.trim(),
        sku: document.getElementById("sku").value.trim().toUpperCase(),
        categoria_id: document.getElementById("categoria").value ? parseInt(document.getElementById("categoria").value) : null,
        tag_id: document.getElementById("tag").value ? parseInt(document.getElementById("tag").value) : null,
        unidade: document.getElementById("unidade").value.trim().toUpperCase(),
        custo: parseCurrency(document.getElementById("custo").value),
        preco: parseCurrency(document.getElementById("preco").value),
        estoque_atual: parseInt(document.getElementById("estoque_atual").value) || 0,
        estoque_minimo: parseInt(document.getElementById("estoque_minimo").value) || 0,
        localizacao: document.getElementById("localizacao").value.trim() || null,
      };

      try {
        if (editingId) {
          await window.api.updateProduto(editingId, payload);
          window.ui.showToast("Produto atualizado com sucesso!", "success");
        } else {
          await window.api.createProduto(payload);
          window.ui.showToast("Produto cadastrado com sucesso!", "success");
        }
        produtoForm.reset();
        produtoModal.hide();
        window.renderProdutos();
      } catch (err) {
        produtoErro.textContent = err.message;
        produtoErro.classList.remove("d-none");
      }
    });

    tbody.addEventListener("click", async (e) => {
      const editBtn = e.target.closest("[data-edit-id]");
      if (editBtn) {
        const id = parseInt(editBtn.dataset.editId);
        const prod = produtos.find(p => p.id === id);
        if (prod) abrirFormulario(prod);
        return;
      }

      const delBtn = e.target.closest("[data-delete-id]");
      if (delBtn) {
        const confirmed = await window.ui.showConfirm({
          title: "Excluir produto",
          message: "Tem certeza que deseja excluir este produto? Esta ação não pode ser desfeita.",
          confirmText: "Excluir",
          danger: true
        });
        if (!confirmed) return;
        try {
          await window.api.deleteProduto(parseInt(delBtn.dataset.deleteId));
          window.ui.showToast("Produto excluído com sucesso!", "success");
          window.renderProdutos();
        } catch (err) {
          window.ui.showToast(err.message, "danger");
        }
        return;
      }
    });

  } catch (error) {
    if (window.ui) {
      ui.showToast("Falha ao abrir produtos: " + ui.getErrorMessage(error), "danger");
      ui.renderInlineError(document.getElementById("produtos-list"), {
        title: "Falha ao carregar produtos",
        message: "A listagem não pôde ser exibida agora.",
        details: ui.getErrorMessage(error),
        tableCols: 6,
        actionLabel: "Tentar novamente",
        action: "window.renderProdutos()"
      });
    }
  }
};
