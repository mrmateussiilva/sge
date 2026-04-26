/* js/views/dashboard.js */
window.renderDashboard = async function () {
    const appContent = document.getElementById("app-content");

    appContent.innerHTML = `
    <header class="page-header d-flex justify-content-between align-items-end flex-wrap gap-2">
      <div>
        <h1>Dashboard</h1>
        <p>Visão geral do sistema de estoque</p>
      </div>
      <div class="text-secondary small"><i class="bi bi-clock me-1"></i>Última atualização: agora</div>
    </header>

    <div class="row g-3" id="dash-metrics">
       <div class="col-12"><div class="text-center py-5 text-muted"><div class="spinner-border text-primary spinner-border-sm me-2"></div>Carregando métricas...</div></div>
    </div>

    <div class="row g-3">
      <div class="col-lg-8">
        <div class="card-enterprise h-100">
          <div class="p-3 border-bottom d-flex justify-content-between align-items-center">
            <h6 class="fw-bold mb-0 text-dark">Movimentações recentes</h6>
            <a href="#/movimentacoes" class="btn btn-sm btn-light">Ver todas</a>
          </div>
          <div class="p-0">
            <div class="table-responsive">
              <table class="table table-compact table-hover mb-0 border-0">
                <thead>
                  <tr>
                    <th class="border-top-0">Produto</th>
                    <th class="border-top-0">Tipo</th>
                    <th class="border-top-0">Qtd.</th>
                    <th class="border-top-0">Motivo</th>
                    <th class="border-top-0">Data</th>
                  </tr>
                </thead>
                <tbody id="dash-movimentacoes">
                   <tr><td colspan="5" class="text-center text-muted py-4">Aguardando dados...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      
      <div class="col-lg-4">
        <div class="card-enterprise h-100 d-flex flex-column">
          <div class="p-3 border-bottom">
            <h6 class="fw-bold mb-0 text-dark">Alertas de Estoque</h6>
          </div>
          <div class="flex-grow-1 p-3 overflow-y-auto" id="dash-alertas" style="max-height: 400px;">
             <!-- Alertas -->
          </div>
        </div>
      </div>
    </div>
  `;

    try {
        const [dashboard, produtos] = await Promise.all([window.api.getDashboard(), window.api.getProdutos()]);
        const zeros = produtos.filter(p => p.estoque_atual === 0).length;

        // Fill metrics
        document.getElementById("dash-metrics").innerHTML = `
      <div class="col-xl-3 col-md-6">
        <div class="card-enterprise p-3 d-flex flex-row align-items-center justify-content-between">
          <div>
            <span class="text-secondary small fw-medium text-uppercase section-label">Total de produtos</span>
            <h3 class="mb-0 fw-bold mt-1 text-dark">${dashboard.total_produtos}</h3>
          </div>
          <div class="bg-primary-subtle text-primary rounded-3 d-flex align-items-center justify-content-center" style="width: 48px; height: 48px;">
            <i class="bi bi-box2 fs-5"></i>
          </div>
        </div>
      </div>
      <div class="col-xl-3 col-md-6">
        <div class="card-enterprise p-3 d-flex flex-row align-items-center justify-content-between">
          <div>
            <span class="text-secondary small fw-medium text-uppercase section-label">Estoque baixo</span>
            <h3 class="mb-0 fw-bold mt-1 text-warning">${dashboard.produtos_com_estoque_baixo.length}</h3>
          </div>
          <div class="bg-warning-subtle text-warning rounded-3 d-flex align-items-center justify-content-center" style="width: 48px; height: 48px;">
            <i class="bi bi-exclamation-triangle fs-5"></i>
          </div>
        </div>
      </div>
      <div class="col-xl-3 col-md-6">
        <div class="card-enterprise p-3 d-flex flex-row align-items-center justify-content-between">
          <div>
            <span class="text-secondary small fw-medium text-uppercase section-label">Estoque zerado</span>
            <h3 class="mb-0 fw-bold mt-1 text-danger">${zeros}</h3>
          </div>
          <div class="bg-danger-subtle text-danger rounded-3 d-flex align-items-center justify-content-center" style="width: 48px; height: 48px;">
            <i class="bi bi-x-circle fs-5"></i>
          </div>
        </div>
      </div>
      <div class="col-xl-3 col-md-6">
        <div class="card-enterprise p-3 d-flex flex-row align-items-center justify-content-between">
          <div>
            <span class="text-secondary small fw-medium text-uppercase section-label">Movimentações</span>
            <h3 class="mb-0 fw-bold mt-1 text-info">${dashboard.ultimas_movimentacoes.length}</h3>
          </div>
          <div class="bg-info-subtle text-info rounded-3 d-flex align-items-center justify-content-center" style="width: 48px; height: 48px;">
            <i class="bi bi-arrow-left-right fs-5"></i>
          </div>
        </div>
      </div>
    `;

        // format tables
        const formatData = (d) => new Date(d).toLocaleString("pt-BR");
        const badgeType = (tipo) => {
            const b = { entrada: "bg-success-subtle", saida: "bg-danger-subtle", ajuste: "bg-info-subtle" }[tipo] || "bg-secondary-subtle";
            return `<span class="badge-status ${b}">${tipo}</span>`;
        };

        const movTable = document.getElementById("dash-movimentacoes");
        if (dashboard.ultimas_movimentacoes.length === 0) {
            movTable.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4"><i class="bi bi-inbox d-block fs-3 mb-2"></i>Nenhuma movimentação</td></tr>`;
        } else {
            movTable.innerHTML = dashboard.ultimas_movimentacoes.map(m => `
         <tr>
           <td><span class="fw-medium text-dark">${m.produto.nome}</span><br/><small class="text-secondary">SKU ${m.produto.sku}</small></td>
           <td>${badgeType(m.tipo)}</td>
           <td class="fw-medium">${m.quantidade} ${m.produto.unidade}</td>
           <td class="text-secondary" style="font-size:0.8rem">${m.motivo || "-"}</td>
           <td><small class="text-secondary">${formatData(m.created_at)}</small></td>
         </tr>
       `).join("");
        }

        // Alerts
        const alertas = document.getElementById("dash-alertas");
        if (dashboard.produtos_com_estoque_baixo.length === 0) {
            alertas.innerHTML = `<div class="text-center text-muted py-5"><i class="bi bi-check-circle fs-1 d-block mb-2 text-success"></i><p>Tudo em ordem no estoque</p></div>`;
        } else {
            alertas.innerHTML = `<div class="d-flex flex-column gap-2">` +
                dashboard.produtos_com_estoque_baixo.slice(0, 8).map(p => {
                    const isZero = p.estoque_atual === 0;
                    return `
        <div class="d-flex align-items-start gap-3 p-2 rounded bg-white border">
           <div class="mt-1 ${isZero ? 'text-danger' : 'text-warning'} fs-5 lh-1"><i class="bi ${isZero ? 'bi-x-octagon-fill' : 'bi-exclamation-triangle-fill'}"></i></div>
           <div class="flex-grow-1 min-vw-0">
             <div class="fw-bold text-dark text-truncate" style="font-size:0.85rem">${p.nome}</div>
             <div class="text-secondary mt-1" style="font-size:0.75rem">Estoque Atual: <strong>${p.estoque_atual}</strong> ${p.unidade}</div>
             <div class="text-secondary" style="font-size:0.75rem">Mínimo: ${p.estoque_minimo}</div>
           </div>
        </div>
        `;
                }).join("") + `</div>`;
        }

    } catch (error) {
        document.getElementById("dash-metrics").innerHTML = `<div class="col-12"><div class="alert alert-danger w-100">${error.message}</div></div>`;
    }
};
