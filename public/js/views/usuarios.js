window.renderUsuarios = async function () {
  const appContent = document.getElementById("app-content");
  const currentUser = window.usuarioAtual ? window.usuarioAtual() : null;

  if (!currentUser || currentUser.perfil !== "admin") {
    if (window.ui) {
      ui.renderPageError(appContent, {
        title: "Acesso restrito",
        message: "Somente administradores podem gerenciar usuários.",
        details: "Entre com um perfil administrador para acessar este módulo.",
        actionLabel: "Voltar ao dashboard",
        action: "window.location.hash = '#/dashboard'"
      });
    }
    return;
  }

  appContent.innerHTML = `
    <header class="mb-3 d-flex flex-column flex-lg-row justify-content-between align-items-lg-end gap-2">
      <div>
        <h1 class="page-title fs-4 fw-bold mb-0 text-dark">Usuários</h1>
        <p class="text-secondary small mb-0 mt-1">Cadastre contas e controle permissões de acesso.</p>
      </div>
      <button class="btn btn-light border bg-white shadow-sm" type="button" onclick="window.renderUsuarios()">
        <i class="bi bi-arrow-clockwise me-2"></i>Atualizar
      </button>
    </header>

    <div class="row g-3">
      <div class="col-xl-4">
        <div class="card-enterprise bg-white border-0 shadow-sm h-100">
          <div class="card-header-polished px-3 py-2 bg-white border-bottom">
            <h6 class="fw-bold mb-0 text-dark" style="font-size:0.85rem">Nova conta</h6>
          </div>
          <div class="p-3">
            <form id="usuarioCreateForm" class="d-flex flex-column gap-3">
              <div>
                <label for="usuarioNome" class="form-label">Nome</label>
                <input id="usuarioNome" type="text" class="form-control bg-light" required placeholder="Nome do usuario">
              </div>
              <div>
                <label for="usuarioEmail" class="form-label">Email</label>
                <input id="usuarioEmail" type="email" class="form-control bg-light" required placeholder="usuario@empresa.com">
              </div>
              <div>
                <label for="usuarioSenha" class="form-label">Senha</label>
                <input id="usuarioSenha" type="password" class="form-control bg-light" required minlength="6" placeholder="Minimo de 6 caracteres">
              </div>
              <div>
                <label for="usuarioPerfil" class="form-label">Perfil</label>
                <select id="usuarioPerfil" class="form-select bg-light">
                  <option value="operador">Operador</option>
                  <option value="admin">Administrador</option>
                </select>
              </div>
              <div id="usuarioCreateErro" class="alert alert-danger py-2 px-3 d-none mb-0" role="alert"></div>
              <button id="usuarioCreateButton" type="submit" class="btn btn-primary">
                <i class="bi bi-person-plus me-2"></i>Criar usuário
              </button>
            </form>
          </div>
        </div>
      </div>

      <div class="col-xl-8">
        <div class="card-enterprise bg-white border-0 shadow-sm">
          <div class="card-header-polished px-3 py-2 bg-white border-bottom d-flex justify-content-between align-items-center">
            <h6 class="fw-bold mb-0 text-dark" style="font-size:0.85rem">Contas cadastradas</h6>
            <span class="text-muted small" id="usuariosCount">Carregando...</span>
          </div>
          <div class="table-responsive">
            <table class="table table-compact mb-0 align-middle">
              <thead>
                <tr>
                  <th class="ps-3">Usuário</th>
                  <th>Email</th>
                  <th>Perfil</th>
                  <th>Status</th>
                  <th class="text-end pe-3">Ações</th>
                </tr>
              </thead>
              <tbody id="usuariosList">
                <tr><td colspan="5" class="p-4"><div class="skeleton w-100" style="height: 58px;"></div></td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  `;

  const tbody = document.getElementById("usuariosList");
  const countEl = document.getElementById("usuariosCount");

  const renderRows = (usuarios) => {
    countEl.textContent = `${usuarios.length} conta(s)`;

    if (!usuarios.length) {
      tbody.innerHTML = `<tr><td colspan="5" class="empty-state py-5"><i class="bi bi-people empty-icon d-block"></i><h6 class="fw-bold text-dark">Nenhum usuário cadastrado</h6></td></tr>`;
      return;
    }

    tbody.innerHTML = usuarios.map((usuario) => {
      const isCurrentUser = usuario.id === currentUser.id;
      return `
        <tr data-usuario-id="${usuario.id}">
          <td class="ps-3" style="min-width: 220px;">
            <input class="form-control form-control-sm bg-light usuario-nome" value="${window.escapeHtml(usuario.nome)}">
            <small class="text-muted d-block mt-1">Criado em ${new Date(usuario.created_at).toLocaleDateString("pt-BR")}${isCurrentUser ? " • voce" : ""}</small>
          </td>
          <td style="min-width: 240px;">
            <input class="form-control form-control-sm bg-light usuario-email" value="${window.escapeHtml(usuario.email)}">
          </td>
          <td style="min-width: 150px;">
            <select class="form-select form-select-sm bg-light usuario-perfil" ${isCurrentUser ? "disabled" : ""}>
              <option value="operador" ${usuario.perfil === "operador" ? "selected" : ""}>Operador</option>
              <option value="admin" ${usuario.perfil === "admin" ? "selected" : ""}>Administrador</option>
            </select>
          </td>
          <td style="min-width: 120px;">
            <select class="form-select form-select-sm bg-light usuario-ativo" ${isCurrentUser ? "disabled" : ""}>
              <option value="true" ${usuario.ativo ? "selected" : ""}>Ativo</option>
              <option value="false" ${!usuario.ativo ? "selected" : ""}>Inativo</option>
            </select>
          </td>
          <td class="text-end pe-3" style="min-width: 150px;">
            <button class="btn btn-sm btn-primary usuario-save">
              <i class="bi bi-check2 me-1"></i>Salvar
            </button>
          </td>
        </tr>
      `;
    }).join("");

    tbody.querySelectorAll(".usuario-save").forEach((button) => {
      button.addEventListener("click", async (event) => {
        const row = event.currentTarget.closest("tr");
        const usuarioId = Number.parseInt(row.dataset.usuarioId, 10);
        const original = event.currentTarget.innerHTML;
        event.currentTarget.disabled = true;
        event.currentTarget.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Salvando';

        try {
          const payload = {
            nome: row.querySelector(".usuario-nome").value.trim(),
            email: row.querySelector(".usuario-email").value.trim(),
            perfil: row.querySelector(".usuario-perfil").value,
            ativo: row.querySelector(".usuario-ativo")?.value !== "false",
          };
          await window.api.updateUsuario(usuarioId, payload);
          if (window.ui) ui.showToast("Usuario atualizado com sucesso.", "success");
          await window.renderUsuarios();
        } catch (error) {
          if (window.ui) ui.showToast(ui.getErrorMessage(error), "danger");
          event.currentTarget.disabled = false;
          event.currentTarget.innerHTML = original;
        }
      });
    });
  };

  try {
    renderRows(await window.api.getUsuarios());
  } catch (error) {
    if (window.ui) {
      ui.showToast("Falha ao carregar usuarios: " + ui.getErrorMessage(error), "danger");
      ui.renderInlineError(tbody, {
        title: "Falha ao carregar usuários",
        message: "A listagem de contas não pôde ser carregada.",
        details: ui.getErrorMessage(error),
        tableCols: 5,
        actionLabel: "Tentar novamente",
        action: "window.renderUsuarios()"
      });
    }
  }

  document.getElementById("usuarioCreateForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const errorBox = document.getElementById("usuarioCreateErro");
    const button = document.getElementById("usuarioCreateButton");
    errorBox.classList.add("d-none");
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Criando...';

    try {
      await window.api.createUsuario({
        nome: document.getElementById("usuarioNome").value.trim(),
        email: document.getElementById("usuarioEmail").value.trim(),
        senha: document.getElementById("usuarioSenha").value,
        perfil: document.getElementById("usuarioPerfil").value,
        ativo: true,
      });
      event.currentTarget.reset();
      if (window.ui) ui.showToast("Usuario criado com sucesso.", "success");
      await window.renderUsuarios();
    } catch (error) {
      errorBox.textContent = window.ui ? ui.getErrorMessage(error) : error.message;
      errorBox.classList.remove("d-none");
      button.disabled = false;
      button.innerHTML = '<i class="bi bi-person-plus me-2"></i>Criar usuário';
    }
  });
};
