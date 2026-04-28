/* js/views/tags.js */
window.renderTags = async function () {
  const appContent = document.getElementById("app-content");
  const appModals = document.getElementById("app-modals");

  appModals.innerHTML = `
    <div class="modal fade" id="tagModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content border-0 shadow-lg">
          <div class="modal-header border-bottom py-3">
            <h5 class="modal-title fw-bold" id="tagModalLabel">Nova tag</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
          </div>
          <div class="modal-body py-4">
            <form id="tagForm" class="row g-3">
              <input type="hidden" id="tagId">
              <div class="col-12">
                <label for="tagNome" class="form-label small fw-medium">Nome *</label>
                <input type="text" class="form-control" id="tagNome" required maxlength="50" placeholder="Ex: Promoção, Novo, Fragil">
              </div>
              <div class="col-12">
                <label for="tagCor" class="form-label small fw-medium">Cor</label>
                <div class="d-flex align-items-center gap-2">
                  <input type="color" class="form-control form-control-color" id="tagCor" value="#6c757d" style="width: 50px; height: 38px; padding: 4px;">
                  <span class="text-muted small">Selecione uma cor para identificar a tag</span>
                </div>
              </div>
              <div class="col-12">
                <div id="tagErro" class="alert alert-danger py-2 mb-0 d-none small"></div>
              </div>
            </form>
          </div>
          <div class="modal-footer border-top py-3">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
            <button type="submit" form="tagForm" class="btn btn-primary px-4">
              <i class="bi bi-check2 me-1"></i> Salvar
            </button>
          </div>
        </div>
      </div>
    </div>
  `;

  appContent.innerHTML = `
    <header class="mb-3">
      <h1 class="page-title fs-4 fw-bold mb-0 text-dark">Tags</h1>
      <p class="text-secondary small mb-0 mt-1">Marque produtos com tags para identificação rápida</p>
    </header>

    <div class="card-enterprise bg-white shadow-sm border-0 mb-3 d-flex flex-wrap align-items-center" style="padding: 14px 16px; gap: 10px;">
      <div class="input-group flex-grow-1" style="flex-basis: 300px; height: var(--input-height);">
        <span class="input-group-text bg-white text-muted border-end-0 ps-3"><i class="bi bi-search"></i></span>
        <input type="text" class="form-control bg-white border-start-0 ps-1 shadow-none h-100" placeholder="Buscar tag..." id="buscaTag">
      </div>
      <button class="btn btn-light border bg-white shadow-sm flex-shrink-0 p-0 d-flex align-items-center justify-content-center" onclick="window.renderTags()" title="Atualizar dados" style="width: var(--input-height); height: var(--input-height);">
        <i class="bi bi-arrow-clockwise text-dark fs-6 lh-1"></i>
      </button>
      <button class="btn btn-primary shadow-sm flex-shrink-0 ms-xl-auto px-3 d-flex align-items-center justify-content-center mt-2 mt-xl-0" id="novaTagBtn" style="height: var(--input-height);">
        <i class="bi bi-plus-lg me-2"></i> Nova Tag
      </button>
    </div>

    <div class="card-enterprise bg-white border-0 shadow-sm p-4">
      <div id="tags-list" class="d-flex flex-wrap gap-2"></div>
    </div>
  `;

  try {
    const tags = await window.api.getTags();
    const tagsList = document.getElementById("tags-list");
    const busca = document.getElementById("buscaTag");

    const renderTags = (lista) => {
      if (lista.length === 0) {
        tagsList.innerHTML = `<div class="empty-state py-5 w-100 text-center"><i class="bi bi-tags empty-icon d-block"></i><h6 class="fw-bold text-dark">Nenhuma tag encontrada.</h6></div>`;
        return;
      }

      tagsList.innerHTML = lista.map(tag => {
        const cor = tag.cor || "#6c757d";
        const textColor = isLightColor(cor) ? "#000" : "#fff";
        return `
          <div class="tag-card d-flex align-items-center gap-2 px-3 py-2 rounded-3 border" style="background-color: ${cor}; border-color: ${adjustColor(cor, -20)} !important;">
            <span class="fw-medium" style="color: ${textColor}; font-size: 0.85rem;">${window.escapeHtml(tag.nome)}</span>
            <div class="d-flex gap-1 ms-2">
              <button class="btn btn-sm p-0 border-0" style="color: ${textColor}; opacity: 0.8;" title="Editar" data-edit-id="${tag.id}">
                <i class="bi bi-pencil" style="font-size: 0.80rem"></i>
              </button>
              <button class="btn btn-sm p-0 border-0" style="color: ${textColor}; opacity: 0.8;" title="Excluir" data-delete-id="${tag.id}">
                <i class="bi bi-trash3" style="font-size: 0.80rem"></i>
              </button>
            </div>
          </div>
        `;
      }).join("");
    };

    function isLightColor(hex) {
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      return (r * 299 + g * 587 + b * 114) / 1000 > 150;
    }

    function adjustColor(hex, amount) {
      const r = Math.max(0, Math.min(255, parseInt(hex.slice(1, 3), 16) + amount));
      const g = Math.max(0, Math.min(255, parseInt(hex.slice(3, 5), 16) + amount));
      const b = Math.max(0, Math.min(255, parseInt(hex.slice(5, 7), 16) + amount));
      return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
    }

    const applyFilters = () => {
      const b = busca.value.toLowerCase().trim();
      const res = tags.filter(t => !b || t.nome.toLowerCase().includes(b));
      renderTags(res);
    };

    busca.addEventListener("input", applyFilters);

    renderTags(tags);

    const tagModal = new bootstrap.Modal(document.getElementById("tagModal"));
    const tagForm = document.getElementById("tagForm");
    const tagErro = document.getElementById("tagErro");
    const tagTitulo = document.getElementById("tagModalLabel");
    let editingId = null;

    function abrirFormulario(tag = null) {
      editingId = tag?.id || null;
      tagForm.reset();
      tagErro.classList.add("d-none");

      if (tag) {
        tagTitulo.textContent = "Editar tag";
        document.getElementById("tagId").value = tag.id;
        document.getElementById("tagNome").value = tag.nome || "";
        document.getElementById("tagCor").value = tag.cor || "#6c757d";
      } else {
        tagTitulo.textContent = "Nova tag";
        document.getElementById("tagId").value = "";
        document.getElementById("tagCor").value = "#6c757d";
      }

      tagModal.show();
    }

    document.getElementById("novaTagBtn").addEventListener("click", () => abrirFormulario());

    tagForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      tagErro.classList.add("d-none");

      const payload = {
        nome: document.getElementById("tagNome").value.trim(),
        cor: document.getElementById("tagCor").value,
      };

      try {
        if (editingId) {
          await window.api.updateTag(editingId, payload);
          window.ui.showToast("Tag atualizada com sucesso!", "success");
        } else {
          await window.api.createTag(payload);
          window.ui.showToast("Tag cadastrada com sucesso!", "success");
        }
        tagForm.reset();
        tagModal.hide();
        window.renderTags();
      } catch (err) {
        tagErro.textContent = err.message;
        tagErro.classList.remove("d-none");
      }
    });

    tagsList.addEventListener("click", async (e) => {
      const editBtn = e.target.closest("[data-edit-id]");
      if (editBtn) {
        const id = parseInt(editBtn.dataset.editId);
        const tag = tags.find(t => t.id === id);
        if (tag) abrirFormulario(tag);
        return;
      }

      const delBtn = e.target.closest("[data-delete-id]");
      if (delBtn) {
        const confirmed = await window.ui.showConfirm({
          title: "Excluir tag",
          message: "Tem certeza que deseja excluir esta tag? Produtos associados ficarão sem tag.",
          confirmText: "Excluir",
          danger: true
        });
        if (!confirmed) return;
        try {
          await window.api.deleteTag(parseInt(delBtn.dataset.deleteId));
          window.ui.showToast("Tag excluída com sucesso!", "success");
          window.renderTags();
        } catch (err) {
          window.ui.showToast(err.message, "danger");
        }
        return;
      }
    });

  } catch (error) {
    if (window.ui) {
      window.ui.showToast("Falha ao carregar tags: " + window.ui.getErrorMessage(error), "danger");
    }
  }
};