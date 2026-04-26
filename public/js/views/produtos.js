/* js/views/produtos.js */
window.renderProdutos = async function () {
  const appContent = document.getElementById("app-content");

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
      <button class="btn btn-primary shadow-sm flex-shrink-0 ms-xl-auto px-3 d-flex align-items-center justify-content-center mt-2 mt-xl-0" onclick="ui.showToast('Recurso em desenvolvimento', 'info')" style="height: var(--input-height);">
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

    const produtos = rawProdutos.map(p => {
      let cat = (p.categoria || "Sem categoria").trim().replace(/\s+/g, ' ');
      if (cat === "") cat = "Sem categoria";
      return { ...p, catNorm: cat };
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

        return `
          <tr>
            <td class="ps-4">
              <div class="d-flex flex-column justify-content-center">
                 <span class="fw-bold text-dark text-truncate" style="max-width: 300px; font-size: 0.90rem; letter-spacing: -0.01em;" title="${p.nome}">${p.nome}</span>
                 <span class="text-muted d-flex align-items-center mt-1" style="font-size: 0.75rem;">
                   <i class="bi bi-tag me-1 opacity-75"></i> ${p.catNorm}
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
                 <button class="btn border border-light-subtle text-secondary p-0 d-flex align-items-center justify-content-center action-btn" style="width:32px; height:32px; border-radius: 6px;" title="Editar">
                    <i class="bi bi-pencil" style="font-size: 0.90rem"></i>
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
