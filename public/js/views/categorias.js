/* js/views/categorias.js */
window.renderCategorias = async function () {
  const appContent = document.getElementById("app-content");
  const appModals = document.getElementById("app-modals");

  appModals.innerHTML = `
    <div class="modal fade" id="categoriaModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content border-0 shadow-lg">
          <div class="modal-header border-bottom py-3">
            <h5 class="modal-title fw-bold" id="categoriaModalLabel">Nova categoria</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
          </div>
          <div class="modal-body py-4">
            <form id="categoriaForm" class="row g-3">
              <input type="hidden" id="categoriaId">
              <div class="col-12">
                <label for="catNome" class="form-label small fw-medium">Nome *</label>
                <input type="text" class="form-control" id="catNome" required maxlength="100" placeholder="Ex: Eletrônicos">
              </div>
              <div class="col-12">
                <label for="catDescricao" class="form-label small fw-medium">Descrição</label>
                <textarea class="form-control" id="catDescricao" rows="2" maxlength="255" placeholder="Descrição opcional"></textarea>
              </div>
              <div class="col-12">
                <div id="categoriaErro" class="alert alert-danger py-2 mb-0 d-none small"></div>
              </div>
            </form>
          </div>
          <div class="modal-footer border-top py-3">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
            <button type="submit" form="categoriaForm" class="btn btn-primary px-4">
              <i class="bi bi-check2 me-1"></i> Salvar
            </button>
          </div>
        </div>
      </div>
    </div>
  `;

  appContent.innerHTML = `
    <header class="mb-3">
      <h1 class="page-title fs-4 fw-bold mb-0 text-dark">Categorias</h1>
      <p class="text-secondary small mb-0 mt-1">Organize seus produtos por categorias</p>
    </header>

    <div class="card-enterprise bg-white shadow-sm border-0 mb-3 d-flex flex-wrap align-items-center" style="padding: 14px 16px; gap: 10px;">
      <div class="input-group flex-grow-1" style="flex-basis: 300px; height: var(--input-height);">
        <span class="input-group-text bg-white text-muted border-end-0 ps-3"><i class="bi bi-search"></i></span>
        <input type="text" class="form-control bg-white border-start-0 ps-1 shadow-none h-100" placeholder="Buscar categoria..." id="buscaCategoria">
      </div>
      <button class="btn btn-light border bg-white shadow-sm flex-shrink-0 p-0 d-flex align-items-center justify-content-center" onclick="window.renderCategorias()" title="Atualizar dados" style="width: var(--input-height); height: var(--input-height);">
        <i class="bi bi-arrow-clockwise text-dark fs-6 lh-1"></i>
      </button>
      <button class="btn btn-primary shadow-sm flex-shrink-0 ms-xl-auto px-3 d-flex align-items-center justify-content-center mt-2 mt-xl-0" id="novaCategoriaBtn" style="height: var(--input-height);">
        <i class="bi bi-plus-lg me-2"></i> Nova Categoria
      </button>
    </div>

    <div class="card-enterprise bg-white border-0 shadow-sm">
      <div class="table-responsive">
        <table class="table table-compact mb-0 border-0">
          <thead class="position-sticky top-0 shadow-sm" style="z-index: 1;">
            <tr>
              <th class="border-start-0 border-top-0 ps-4 text-dark" style="width: 40%;">Nome</th>
              <th class="border-top-0 text-dark">Descrição</th>
              <th class="text-end border-end-0 border-top-0 pe-4 text-dark" style="min-width: 110px;">Ações</th>
            </tr>
          </thead>
          <tbody id="categorias-list">
            <tr>
              <td colspan="3">
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
  `;

  try {
    const categorias = await window.api.getCategorias();
    const tbody = document.getElementById("categorias-list");
    const busca = document.getElementById("buscaCategoria");

    const renderTable = (lista) => {
      if (lista.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" class="empty-state py-5"><i class="bi bi-tags empty-icon d-block"></i><h6 class="fw-bold text-dark">Nenhuma categoria encontrada.</h6></td></tr>`;
        return;
      }

      tbody.innerHTML = lista.map(cat => `
        <tr>
          <td class="ps-4">
            <div class="d-flex flex-column justify-content-center">
              <span class="fw-bold text-dark" style="font-size: 0.90rem;">${window.escapeHtml(cat.nome)}</span>
            </div>
          </td>
          <td class="text-secondary" style="font-size: 0.85rem;">${window.escapeHtml(cat.descricao || '-')}</td>
          <td class="text-end pe-4">
            <div class="d-flex justify-content-end gap-2 actions-group">
              <button class="btn border border-light-subtle text-secondary p-0 d-flex align-items-center justify-content-center action-btn" style="width:32px; height:32px; border-radius: 6px;" title="Editar" data-edit-id="${cat.id}">
                <i class="bi bi-pencil" style="font-size: 0.90rem"></i>
              </button>
              <button class="btn border border-light-subtle text-danger p-0 d-flex align-items-center justify-content-center action-btn" style="width:32px; height:32px; border-radius: 6px;" title="Excluir" data-delete-id="${cat.id}">
                <i class="bi bi-trash3" style="font-size: 0.90rem"></i>
              </button>
            </div>
          </td>
        </tr>
      `).join("");
    };

    const applyFilters = () => {
      const b = busca.value.toLowerCase().trim();
      const res = categorias.filter(c =>
        !b || c.nome.toLowerCase().includes(b) || (c.descricao && c.descricao.toLowerCase().includes(b))
      );
      renderTable(res);
    };

    busca.addEventListener("input", applyFilters);

    renderTable(categorias);

    const categoriaModal = new bootstrap.Modal(document.getElementById("categoriaModal"));
    const categoriaForm = document.getElementById("categoriaForm");
    const categoriaErro = document.getElementById("categoriaErro");
    const categoriaTitulo = document.getElementById("categoriaModalLabel");
    let editingId = null;

    function abrirFormulario(categoria = null) {
      editingId = categoria?.id || null;
      categoriaForm.reset();
      categoriaErro.classList.add("d-none");

      if (categoria) {
        categoriaTitulo.textContent = "Editar categoria";
        document.getElementById("categoriaId").value = categoria.id;
        document.getElementById("catNome").value = categoria.nome || "";
        document.getElementById("catDescricao").value = categoria.descricao || "";
      } else {
        categoriaTitulo.textContent = "Nova categoria";
        document.getElementById("categoriaId").value = "";
      }

      categoriaModal.show();
    }

    document.getElementById("novaCategoriaBtn").addEventListener("click", () => abrirFormulario());

    categoriaForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      categoriaErro.classList.add("d-none");

      const payload = {
        nome: document.getElementById("catNome").value.trim(),
        descricao: document.getElementById("catDescricao").value.trim() || null,
      };

      try {
        if (editingId) {
          await window.api.updateCategoria(editingId, payload);
          window.ui.showToast("Categoria atualizada com sucesso!", "success");
        } else {
          await window.api.createCategoria(payload);
          window.ui.showToast("Categoria cadastrada com sucesso!", "success");
        }
        categoriaForm.reset();
        categoriaModal.hide();
        window.renderCategorias();
      } catch (err) {
        categoriaErro.textContent = err.message;
        categoriaErro.classList.remove("d-none");
      }
    });

    tbody.addEventListener("click", async (e) => {
      const editBtn = e.target.closest("[data-edit-id]");
      if (editBtn) {
        const id = parseInt(editBtn.dataset.editId);
        const cat = categorias.find(c => c.id === id);
        if (cat) abrirFormulario(cat);
        return;
      }

      const delBtn = e.target.closest("[data-delete-id]");
      if (delBtn) {
        const confirmed = await window.ui.showConfirm({
          title: "Excluir categoria",
          message: "Tem certeza que deseja excluir esta categoria? Produtos associados ficarão sem categoria.",
          confirmText: "Excluir",
          danger: true
        });
        if (!confirmed) return;
        try {
          await window.api.deleteCategoria(parseInt(delBtn.dataset.deleteId));
          window.ui.showToast("Categoria excluída com sucesso!", "success");
          window.renderCategorias();
        } catch (err) {
          window.ui.showToast(err.message, "danger");
        }
        return;
      }
    });

  } catch (error) {
    if (window.ui) {
      window.ui.showToast("Falha ao carregar categorias: " + window.ui.getErrorMessage(error), "danger");
      window.ui.renderInlineError(document.getElementById("categorias-list"), {
        title: "Falha ao carregar categorias",
        message: "A listagem não pôde ser exibida agora.",
        details: window.ui.getErrorMessage(error),
        tableCols: 3,
        actionLabel: "Tentar novamente",
        action: "window.renderCategorias()"
      });
    }
  }
};