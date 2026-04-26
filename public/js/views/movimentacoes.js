/* js/views/movimentacoes.js */
window.renderMovimentacoes = async function () {
  const appContent = document.getElementById("app-content");

  appContent.innerHTML = `
    <!-- Dense Page Header Pattern -->
    <header class="d-flex justify-content-between align-items-center mb-2">
      <div>
        <h1 class="fs-4 fw-bold mb-0 text-dark">Movimentações</h1>
        <p class="text-secondary small mb-0 mt-1">Lançamento de fluxo contínuo de estoque</p>
      </div>
    </header>

    <div class="row g-3 mb-2">
      <div class="col-xl-4 col-lg-5">
        <div class="card-enterprise h-100 d-flex flex-column shadow-sm border-0 position-sticky" style="top: 10px;">
          <div class="card-header-polished px-3 py-2 d-flex align-items-center bg-white">
            <h6 class="fw-bold mb-0 text-dark" style="font-size:0.85rem"><i class="bi bi-arrow-down-up text-primary me-2"></i>Lançar Registro</h6>
          </div>
          <div class="p-3 flex-grow-1 bg-white" style="border-bottom-left-radius:8px; border-bottom-right-radius:8px;">
            <form id="form-movimentacao" class="d-flex flex-column h-100 gap-2">
              <div class="form-group mb-1">
                <label class="form-label">Natureza da operação</label>
                <div class="segmented-group d-flex w-100">
                  <input type="radio" class="btn-check" name="tipoMov" id="tipoEnt" value="entrada" checked>
                  <label class="btn btn-outline-success flex-grow-1" for="tipoEnt">Entrada</label>
                  
                  <input type="radio" class="btn-check" name="tipoMov" id="tipoSai" value="saida">
                  <label class="btn btn-outline-danger flex-grow-1" for="tipoSai">Saída</label>

                  <input type="radio" class="btn-check" name="tipoMov" id="tipoAju" value="ajuste">
                  <label class="btn btn-outline-secondary flex-grow-1" for="tipoAju">Ajuste</label>
                </div>
              </div>

              <div class="form-group">
                <label for="produtoId" class="form-label">Produto alvo</label>
                <select class="form-select bg-light" id="produtoId" required aria-label="Selecione o produto">
                  <option value="">Carregando dados...</option>
                </select>
              </div>

              <div class="form-group">
                 <label for="quantidade" class="form-label">Quantidade</label>
                 <input type="number" class="form-control fw-bold fs-6" id="quantidade" min="1" step="1" inputmode="numeric" required placeholder="Inteiro" aria-label="Quantidade">
              </div>

              <div class="form-group flex-grow-1 d-flex flex-column">
                 <label for="motivo" class="form-label d-flex justify-content-between">
                    Justificativa <span class="text-secondary fw-normal">Opcional</span>
                 </label>
                 <textarea class="form-control bg-light flex-grow-1" id="motivo" placeholder="Detalhes (ex: avaria, doação)" style="resize: none; min-height: 70px;" aria-label="Motivo"></textarea>
              </div>

              <button type="submit" class="btn btn-primary w-100 mt-2 shadow-sm" id="btnSalvarMov" aria-label="Salvar movimentação">
                <i class="bi bi-check2-circle me-1"></i> Confirmar
              </button>
            </form>
          </div>
        </div>
      </div>

      <div class="col-xl-8 col-lg-7">
        <div class="card-enterprise h-100 d-flex flex-column">
          <div class="card-header-polished px-3 py-2 d-flex justify-content-between align-items-center bg-white">
             <h6 class="fw-bold mb-0 text-dark" style="font-size:0.85rem"><i class="bi bi-card-list text-secondary me-2"></i>Histórico Recente</h6>
             <button class="btn btn-sm btn-icon-sm btn-light border shadow-sm" onclick="renderMovimentacoes()" title="Recarregar tabela" aria-label="Atualizar histórico">
                <i class="bi bi-arrow-clockwise"></i>
             </button>
          </div>
          <div class="table-responsive flex-grow-1">
            <table class="table table-compact table-hover mb-0 border-0 w-100">
              <thead>
                <tr>
                  <th class="border-top-0 border-start-0 ps-3" style="width: 25%">Data/Hora</th>
                  <th class="border-top-0" style="width: 40%">Produto</th>
                  <th class="border-top-0 text-center">Tipo</th>
                  <th class="border-top-0 text-end pe-3">Montante</th>
                </tr>
              </thead>
              <tbody id="movimentacoes-list">
                <tr><td colspan="4" class="py-4 px-4"><div class="skeleton mb-2" style="height:38px;"></div><div class="skeleton mb-2" style="height:38px;"></div><div class="skeleton" style="height:38px;"></div></td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  `;

  try {
    const [movimentacoes, produtos] = await Promise.all([
      window.api.getMovimentacoes(),
      window.api.getProdutos()
    ]);

    const select = document.getElementById("produtoId");
    if (produtos.length === 0) {
      select.innerHTML = '<option value="">Estoque vazio.</option>';
      select.disabled = true;
    } else {
      select.innerHTML = '<option value="">-- Selecionar item --</option>' +
        produtos.sort((a, b) => a.nome.localeCompare(b.nome)).map(p => `<option value="${p.id}">${p.nome} (Estq: ${p.estoque_atual})</option>`).join("");
    }

    const renderTable = () => {
      const tbody = document.getElementById("movimentacoes-list");
      if (movimentacoes.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="empty-state py-4"><i class="bi bi-ui-checks empty-icon d-block"></i><h6 class="fw-bold">Nenhum registro</h6></td></tr>`;
        return;
      }

      const formatData = (d) => {
        const dt = new Date(d);
        return `<span class="fw-medium text-dark">${dt.toLocaleDateString('pt-BR')}</span> <br><small class="text-muted" style="font-size:0.7rem">${dt.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</small>`;
      };

      const styleType = (tipo) => {
        const t = {
          entrada: { b: 'bg-success-subtle', c: 'text-success', i: 'bi-box-arrow-in-right', sign: '+' },
          saida: { b: 'bg-danger-subtle', c: 'text-danger', i: 'bi-box-arrow-up-right', sign: '-' },
          ajuste: { b: 'bg-info-subtle', c: 'text-primary', i: 'bi-sliders', sign: '' }
        }[tipo] || { b: 'bg-secondary', c: 'text-secondary', i: 'bi-record', sign: '' };
        return {
          badge: `<div class="badge-status ${t.b} px-2 py-1"><i class="bi ${t.i} me-1"></i><span class="text-uppercase">${tipo}</span></div>`,
          color: t.c,
          sign: t.sign
        };
      };

      tbody.innerHTML = movimentacoes.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).map(m => {
        const op = styleType(m.tipo);
        return `
        <tr>
          <td class="ps-3 align-middle" style="white-space:nowrap">${formatData(m.created_at)}</td>
          <td class="align-middle">
             <div class="fw-bold text-dark text-truncate" style="max-width:240px; font-size:0.85rem" title="${m.produto.nome}">${m.produto.nome}</div>
             <div class="d-flex align-items-center gap-2 mt-1">
                 <div class="text-secondary font-monospace" style="font-size:0.7rem">${m.produto.sku}</div>
                 ${m.motivo ? `<div class="text-truncate text-muted" style="max-width:120px; font-size:0.7rem" title="${m.motivo}"><i class="bi bi-chat-text mx-1"></i>${m.motivo}</div>` : ''}
             </div>
          </td>
          <td class="align-middle text-center">${op.badge}</td>
          <td class="align-middle text-end pe-3">
             <strong class="${op.color} fs-6">${op.sign}${m.quantidade}</strong>
             <div class="text-muted mt-1" style="font-size:0.7rem">${m.produto.unidade}</div>
          </td>
        </tr>
      `}).join("");
    };

    renderTable();

    const quantidadeInput = document.getElementById("quantidade");
    if (window.enforceIntegerInput) {
      window.enforceIntegerInput(quantidadeInput, { min: 1 });
    }

    document.getElementById("form-movimentacao").addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = document.getElementById("btnSalvarMov");
      btn.disabled = true;
      const originalText = btn.innerHTML;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>...';

      try {
        const quantidade = Number.parseInt(quantidadeInput.value, 10);

        if (!Number.isInteger(quantidade) || quantidade < 1) {
          throw new Error("Informe uma quantidade inteira maior que zero.");
        }

        const payload = {
          produto_id: parseInt(document.getElementById("produtoId").value),
          tipo: document.querySelector('input[name="tipoMov"]:checked').value,
          quantidade,
          motivo: document.getElementById("motivo").value.trim() || null
        };
        const nova = await window.api.createMovimentacao(payload);
        movimentacoes.push(nova);
        renderTable();
        document.getElementById("form-movimentacao").reset();
        if (window.ui) ui.showToast("Registrado!", "success");
      } catch (err) {
        if (window.ui) ui.showToast("Não foi possível salvar a movimentação: " + ui.getErrorMessage(err), "danger");
      } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
      }
    });

  } catch (error) {
    if (window.ui) {
      ui.showToast("Falha ao carregar movimentações: " + ui.getErrorMessage(error), "danger");
      ui.renderInlineError(document.getElementById("movimentacoes-list"), {
        title: "Falha ao carregar movimentações",
        message: "O histórico e o formulário dependem de dados que não foram carregados.",
        details: ui.getErrorMessage(error),
        tableCols: 4,
        actionLabel: "Recarregar módulo",
        action: "window.renderMovimentacoes()"
      });
    }
  }
};
