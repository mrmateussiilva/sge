/* js/views/produtos.js */
window.renderProdutos = async function () {
    const appContent = document.getElementById("app-content");

    appContent.innerHTML = `
    <header class="page-header d-flex justify-content-between align-items-end flex-wrap gap-3">
      <div>
        <h1>Produtos</h1>
        <p>Cadastro e consulta de itens em estoque</p>
      </div>
      <button class="btn btn-primary" onclick="alert('Funcionalidade sendo conectada em breve')">
        <i class="bi bi-plus-lg me-1"></i> Adicionar produto
      </button>
    </header>

    <div class="card-enterprise">
      <div class="p-3 border-bottom d-flex gap-2 flex-wrap bg-light rounded-top">
        <div class="input-group" style="max-width: 300px;">
          <span class="input-group-text bg-white border-end-0 text-secondary"><i class="bi bi-search"></i></span>
          <input type="text" class="form-control border-start-0 ps-0" placeholder="Buscar por código ou nome..." id="buscaProduto">
        </div>
        <select class="form-select" style="max-width: 150px;" id="filtroStatus">
          <option value="">Status (Todos)</option>
          <option value="ok">Estoque Normal</option>
          <option value="low">Estoque Baixo</option>
          <option value="zero">Zerado</option>
        </select>
      </div>

      <div class="table-responsive">
        <table class="table table-compact table-hover mb-0 border-0">
          <thead>
            <tr>
              <th class="border-top-0 border-start-0">Produto</th>
              <th class="border-top-0">SKU / Cód.</th>
              <th class="border-top-0">Categoria</th>
              <th class="border-top-0 text-end">Estoque</th>
              <th class="border-top-0 text-end">Mínimo</th>
              <th class="border-top-0">Status</th>
              <th class="border-top-0 text-end border-end-0">Ações</th>
            </tr>
          </thead>
          <tbody id="produtos-list">
            <tr><td colspan="7" class="text-center py-4 text-muted"><div class="spinner-border spinner-border-sm text-primary me-2"></div> Carregando...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  `;

    try {
        const produtos = await window.api.getProdutos();
        const renderTable = (lista) => {
            const tbody = document.getElementById("produtos-list");
            if (lista.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center py-5 text-muted"><i class="bi bi-inbox fs-1 d-block mb-2"></i>Nenhum produto cadastrado</td></tr>`;
                return;
            }
            tbody.innerHTML = lista.map(p => {
                let status = "ok", badge = "bg-success-subtle", lbl = "Normal";
                if (p.estoque_atual === 0) {
                    status = "zero"; badge = "bg-danger-subtle"; lbl = "Zerado";
                } else if (p.estoque_atual <= p.estoque_minimo) {
                    status = "low"; badge = "bg-warning-subtle"; lbl = "Baixo";
                }

                return `
          <tr>
            <td class="fw-medium text-dark">${p.nome}</td>
            <td class="text-secondary"><span class="badge bg-light text-dark border font-monospace">${p.sku}</span></td>
            <td><span class="badge border bg-transparent text-secondary">${p.categoria || 'Geral'}</span></td>
            <td class="text-end fw-bold">${p.estoque_atual} <span class="fw-normal text-muted" style="font-size:0.75rem">${p.unidade}</span></td>
            <td class="text-end text-muted">${p.estoque_minimo}</td>
            <td><span class="badge-status ${badge}">${lbl}</span></td>
            <td class="text-end">
               <button class="btn btn-icon btn-light border" title="Editar"><i class="bi bi-pencil"></i></button>
               <button class="btn btn-icon btn-light border text-danger" title="Excluir"><i class="bi bi-trash"></i></button>
            </td>
          </tr>
        `;
            }).join("");
        };

        renderTable(produtos);

        // Simple Filtering
        const busca = document.getElementById("buscaProduto");
        const filtro = document.getElementById("filtroStatus");

        const applyFilters = () => {
            const b = busca.value.toLowerCase();
            const f = filtro.value;
            const res = produtos.filter(p => {
                const matchBusca = p.nome.toLowerCase().includes(b) || p.sku.toLowerCase().includes(b);
                let status = "ok";
                if (p.estoque_atual === 0) status = "zero";
                else if (p.estoque_atual <= p.estoque_minimo) status = "low";
                const matchStatus = !f || f === status;
                return matchBusca && matchStatus;
            });
            renderTable(res);
        };

        busca.addEventListener("input", applyFilters);
        filtro.addEventListener("change", applyFilters);

    } catch (error) {
        document.getElementById("produtos-list").innerHTML = `<tr><td colspan="7" class="text-center py-4 text-danger">${error.message}</td></tr>`;
    }
};
