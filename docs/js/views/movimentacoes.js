/* js/views/movimentacoes.js */
window.renderMovimentacoes = async function () {
    const appContent = document.getElementById("app-content");

    appContent.innerHTML = `
    <header class="page-header d-flex justify-content-between align-items-end flex-wrap gap-3">
      <div>
        <h1>Movimentações</h1>
        <p>Registre entradas, saídas e ajustes de estoque</p>
      </div>
    </header>

    <div class="row g-4">
      <div class="col-lg-4">
        <div class="card-enterprise form-panel">
          <div class="p-3 border-bottom bg-light rounded-top">
            <h6 class="fw-bold mb-0 text-dark">Nova Movimentação</h6>
          </div>
          <div class="p-4">
            <form id="form-movimentacao">
              <div class="mb-3">
                <label class="form-label form-label-sm fw-medium">Tipo</label>
                <div class="d-flex gap-2">
                  <input type="radio" class="btn-check" name="tipoMov" id="tipoEnt" value="entrada" checked>
                  <label class="btn btn-outline-success flex-grow-1" for="tipoEnt">Entrada</label>
                  
                  <input type="radio" class="btn-check" name="tipoMov" id="tipoSai" value="saida">
                  <label class="btn btn-outline-danger flex-grow-1" for="tipoSai">Saída</label>

                  <input type="radio" class="btn-check" name="tipoMov" id="tipoAju" value="ajuste">
                  <label class="btn btn-outline-secondary flex-grow-1" for="tipoAju">Ajuste</label>
                </div>
              </div>
              <div class="mb-3">
                <label class="form-label form-label-sm fw-medium">Produto</label>
                <select class="form-select" id="produtoId" required>
                  <option value="">Carregando produtos...</option>
                </select>
              </div>
              <div class="row g-2 mb-3">
                 <div class="col-6">
                    <label class="form-label form-label-sm fw-medium">Quantidade</label>
                    <input type="number" class="form-control" id="quantidade" min="1" required>
                 </div>
                 <div class="col-6">
                    <label class="form-label form-label-sm fw-medium">Motivo (opcional)</label>
                    <input type="text" class="form-control" id="motivo" placeholder="Ex: Compra">
                 </div>
              </div>
              <button type="submit" class="btn btn-primary w-100" id="btnSalvarMov">
                Salvar Movimentação
              </button>
            </form>
          </div>
        </div>
      </div>

      <div class="col-lg-8">
        <div class="card-enterprise h-100">
          <div class="p-3 border-bottom bg-light rounded-top d-flex justify-content-between align-items-center">
             <h6 class="fw-bold mb-0 text-dark">Histórico de Movimentações</h6>
             <button class="btn btn-sm btn-icon btn-light border" title="Visualização expandida"><i class="bi bi-arrows-fullscreen"></i></button>
          </div>
          <div class="table-responsive">
            <table class="table table-compact table-hover mb-0 border-0">
              <thead>
                <tr>
                  <th class="border-top-0 border-start-0">Data</th>
                  <th class="border-top-0">Produto</th>
                  <th class="border-top-0">Tipo</th>
                  <th class="border-top-0 text-end">Qtd.</th>
                  <th class="border-top-0 border-end-0">Motivo</th>
                </tr>
              </thead>
              <tbody id="movimentacoes-list">
                <tr><td colspan="5" class="text-center py-4 text-muted"><div class="spinner-border spinner-border-sm me-2"></div> Carregando...</td></tr>
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

        // Populate Select
        const select = document.getElementById("produtoId");
        if (produtos.length === 0) {
            select.innerHTML = '<option value="">Crie um produto primeiro</option>';
            select.disabled = true;
        } else {
            select.innerHTML = '<option value="">Selecione...</option>' + produtos.map(p => `
         <option value="${p.id}">${p.nome} (SKU: ${p.sku})</option>
       `).join("");
        }

        // Render Table
        const renderTable = () => {
            const tbody = document.getElementById("movimentacoes-list");
            if (movimentacoes.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center py-5 text-muted"><i class="bi bi-clock-history fs-1 d-block mb-2"></i>Nenhum registro ainda</td></tr>`;
                return;
            }

            const formatData = (d) => {
                const dt = new Date(d);
                return `<span class="fw-medium">${dt.toLocaleDateString('pt-BR')}</span> <small class="text-secondary">${dt.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</small>`;
            };

            const badgeType = (tipo) => {
                const b = { entrada: "bg-success-subtle", saida: "bg-danger-subtle", ajuste: "bg-info-subtle" }[tipo] || "bg-secondary-subtle";
                return `<span class="badge-status ${b}">${tipo}</span>`;
            };

            tbody.innerHTML = movimentacoes.sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).map(m => `
        <tr>
          <td>${formatData(m.created_at)}</td>
          <td><span class="fw-medium text-dark">${m.produto.nome}</span></td>
          <td>${badgeType(m.tipo)}</td>
          <td class="text-end fw-bold">${m.quantidade} <small class="text-muted fw-normal">${m.produto.unidade}</small></td>
          <td class="text-secondary" style="font-size:0.8rem">${m.motivo || "-"}</td>
        </tr>
      `).join("");
        };

        renderTable();

        // Form Submit
        document.getElementById("form-movimentacao").addEventListener("submit", async (e) => {
            e.preventDefault();
            const btn = document.getElementById("btnSalvarMov");
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Salvando...';

            try {
                const payload = {
                    produto_id: parseInt(document.getElementById("produtoId").value),
                    tipo: document.querySelector('input[name="tipoMov"]:checked').value,
                    quantidade: parseInt(document.getElementById("quantidade").value),
                    motivo: document.getElementById("motivo").value.trim() || null
                };
                const nova = await window.api.createMovimentacao(payload);
                movimentacoes.push(nova);
                renderTable();
                document.getElementById("form-movimentacao").reset();
            } catch (err) {
                alert(err.message);
            } finally {
                btn.disabled = false;
                btn.innerHTML = 'Salvar Movimentação';
            }
        });

    } catch (error) {
        document.getElementById("movimentacoes-list").innerHTML = `<tr><td colspan="5" class="text-center py-4 text-danger">${error.message}</td></tr>`;
    }
};
