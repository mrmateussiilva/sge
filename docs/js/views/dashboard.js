/* js/views/dashboard.js */
window.renderDashboard = async function () {
  const appContent = document.getElementById("app-content");

  appContent.innerHTML = `
    <!-- Dense Page Header Pattern -->
    <header class="d-flex justify-content-between align-items-center mb-2">
      <div>
        <h1 class="page-title fs-4 fw-bold mb-0 text-dark">Dashboard</h1>
        <p class="text-secondary small mb-0 mt-1">Visão geral e resumo operacional</p>
      </div>
      <button class="btn btn-light shadow-sm border" onclick="window.renderDashboard()" title="Atualizar dados">
        <i class="bi bi-arrow-clockwise me-1"></i> Recarregar
      </button>
    </header>

    <div class="row g-2 mb-2" id="dash-metrics">
       <div class="col-12"><div class="skeleton rounded-3" style="height: 84px; width: 100%;"></div></div>
    </div>

    <div class="row g-2 mb-2">
      <div class="col-lg-8">
        <div class="card-enterprise h-100 d-flex flex-column">
          <div class="card-header-polished px-3 py-2 d-flex justify-content-between align-items-center bg-white">
            <h6 class="fw-bold mb-0 text-dark" style="font-size:0.85rem">Lançamentos Recentes</h6>
            <a href="#/movimentacoes" class="btn btn-sm btn-light border py-1" style="font-size:0.75rem">Ver Tudo</a>
          </div>
          <div class="p-0 flex-grow-1 overflow-auto">
            <div class="table-responsive h-100">
              <table class="table table-compact mb-0 border-0">
                <thead>
                  <tr>
                    <th class="border-top-0 border-start-0 ps-3">Data</th>
                    <th class="border-top-0">Operação</th>
                    <th class="border-top-0 border-end-0 text-end pe-3">Resumo</th>
                  </tr>
                </thead>
                <tbody id="dash-movimentacoes">
                   <tr><td colspan="3" class="p-4"><div class="skeleton w-100 mb-2" style="height: 34px;"></div></td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      
      <div class="col-lg-4">
        <div class="card-enterprise h-100 d-flex flex-column">
          <div class="card-header-polished px-3 py-2 bg-white">
            <h6 class="fw-bold mb-0 text-dark" style="font-size:0.85rem">Demandam Atenção</h6>
          </div>
          <div class="flex-grow-1 p-2 overflow-y-auto bg-light" id="dash-alertas" style="max-height: 360px;">
             <div class="p-2"><div class="skeleton w-100 mb-2" style="height: 52px;"></div></div>
          </div>
        </div>
      </div>
    </div>
  `;

  try {
    const [dashboard, produtos] = await Promise.all([window.api.getDashboard(), window.api.getProdutos()]);
    const zeros = produtos.filter(p => p.estoque_atual === 0).length;
    const ok = produtos.length - dashboard.produtos_com_estoque_baixo.length;

    document.getElementById("dash-metrics").innerHTML = `
      <div class="col-xl-3 col-md-6">
        <div class="card-enterprise p-3 d-flex flex-row align-items-center justify-content-between h-100 border-0 bg-white">
          <div>
            <span class="text-secondary fw-bold text-uppercase section-label">Acervo Total</span>
            <div class="d-flex align-items-baseline gap-2 mt-1">
               <h3 class="mb-0 fw-bold text-dark lh-1 fs-4">${dashboard.total_produtos}</h3>
            </div>
          </div>
          <div class="bg-primary-subtle text-primary rounded-3 d-flex align-items-center justify-content-center flex-shrink-0" style="width: 42px; height: 42px;">
            <i class="bi bi-box-seam fs-5"></i>
          </div>
        </div>
      </div>
      <div class="col-xl-3 col-md-6">
        <div class="card-enterprise p-3 d-flex flex-row align-items-center justify-content-between h-100 border-0 bg-white">
          <div>
            <span class="text-secondary fw-bold text-uppercase section-label">Saudável</span>
            <div class="d-flex align-items-baseline gap-2 mt-1">
               <h3 class="mb-0 fw-bold text-success lh-1 fs-4">${ok}</h3>
            </div>
          </div>
          <div class="bg-success-subtle text-success rounded-3 d-flex align-items-center justify-content-center flex-shrink-0" style="width: 42px; height: 42px;">
            <i class="bi bi-check2-circle fs-5"></i>
          </div>
        </div>
      </div>
      <div class="col-xl-3 col-md-6">
        <div class="card-enterprise p-3 d-flex flex-row align-items-center justify-content-between h-100 border-0 bg-white">
          <div>
            <span class="text-secondary fw-bold text-uppercase section-label">Baixo Estoque</span>
            <div class="d-flex align-items-baseline gap-2 mt-1">
               <h3 class="mb-0 fw-bold text-warning lh-1 fs-4">${dashboard.produtos_com_estoque_baixo.length - zeros}</h3>
            </div>
          </div>
          <div class="bg-warning-subtle text-warning rounded-3 d-flex align-items-center justify-content-center flex-shrink-0" style="width: 42px; height: 42px;">
            <i class="bi bi-exclamation-triangle fs-5"></i>
          </div>
        </div>
      </div>
      <div class="col-xl-3 col-md-6">
        <div class="card-enterprise p-3 d-flex flex-row align-items-center justify-content-between h-100 border-0 bg-white border-start border-danger border-4">
          <div>
            <span class="text-secondary fw-bold text-uppercase section-label">Zerados</span>
            <div class="d-flex align-items-baseline gap-2 mt-1">
               <h3 class="mb-0 fw-bold text-danger lh-1 fs-4">${zeros}</h3>
            </div>
          </div>
          <div class="bg-danger-subtle text-danger rounded-3 d-flex align-items-center justify-content-center flex-shrink-0" style="width: 42px; height: 42px;">
            <i class="bi bi-dash-circle fs-5"></i>
          </div>
        </div>
      </div>
    `;

    const formatData = (d) => {
      const dt = new Date(d);
      return `<strong class="text-dark d-block mb-0" style="font-size:0.8rem">${dt.toLocaleDateString("pt-BR")}</strong><span class="text-muted font-monospace" style="font-size:0.7rem">${dt.toLocaleTimeString("pt-BR", { hour: '2-digit', minute: '2-digit' })}</span>`;
    };
    const badgeType = (tipo) => {
      const b = { entrada: "bg-success-subtle", saida: "bg-danger-subtle", ajuste: "bg-info-subtle" }[tipo] || "bg-secondary-subtle";
      return `<div class="badge-status ${b} text-uppercase lh-1" style="font-size: 0.60rem; padding: 3px 5px;">${tipo}</div>`;
    };

    const movTable = document.getElementById("dash-movimentacoes");
    if (dashboard.ultimas_movimentacoes.length === 0) {
      movTable.innerHTML = `<tr><td colspan="3" class="empty-state py-4"><i class="bi bi-archive empty-icon d-block fs-3"></i><h6 class="text-secondary fw-medium fs-6">Auditoria inativa</h6></td></tr>`;
    } else {
      movTable.innerHTML = dashboard.ultimas_movimentacoes.slice(0, 6).map(m => `
         <tr>
           <td class="ps-3 align-middle" style="width: 20%">${formatData(m.created_at)}</td>
           <td class="align-middle">
             <div class="fw-bold text-dark text-truncate" style="max-width: 240px; font-size: 0.85rem" title="${m.produto.nome}">${m.produto.nome}</div>
             <div class="d-flex align-items-center gap-2">
               <span class="text-muted fw-normal font-monospace" style="font-size:0.7rem">${m.produto.sku}</span>
             </div>
           </td>
           <td class="pe-3 align-middle text-end" style="width: 25%">
             <div class="d-flex flex-column align-items-end gap-1">
               <strong class="fs-6 lh-1 ${m.tipo === 'entrada' ? 'text-success' : (m.tipo === 'saida' ? 'text-danger' : 'text-primary')}">${m.tipo === 'entrada' ? '+' : (m.tipo === 'saida' ? '-' : '')}${m.quantidade}</strong>
               ${badgeType(m.tipo)}
             </div>
           </td>
         </tr>
       `).join("");
    }

    const alertas = document.getElementById("dash-alertas");
    if (dashboard.produtos_com_estoque_baixo.length === 0) {
      alertas.innerHTML = `<div class="empty-state py-4 mt-2"><i class="bi bi-shield-check text-success fs-2 mb-2 d-block"></i><span class="text-secondary fw-semibold">Estoque Saudável</span></div>`;
    } else {
      alertas.innerHTML = `<div class="d-flex flex-column gap-2 mb-1">` +
        dashboard.produtos_com_estoque_baixo.slice(0, 6).map(p => {
          const isZero = p.estoque_atual === 0;
          return `
        <div class="d-flex gap-2 p-2 px-3 rounded-2 bg-white border shadow-sm align-items-center">
           <div class="${isZero ? 'text-danger bg-danger-subtle' : 'text-warning bg-warning-subtle'} rounded d-flex align-items-center justify-content-center flex-shrink-0" style="width:28px; height:28px;">
              <i class="bi ${isZero ? 'bi-x-octagon-fill' : 'bi-exclamation-triangle-fill'}" style="font-size:0.9rem"></i>
           </div>
           <div class="flex-grow-1 min-vw-0">
             <div class="fw-bold text-dark text-truncate lh-1 mb-1" style="font-size:0.8rem" title="${p.nome}">${p.nome} 
               <span class="text-secondary font-monospace fw-normal ms-1" style="font-size:0.65rem">${p.sku}</span>
             </div>
             <div class="d-flex justify-content-between align-items-baseline lh-1">
                 <span class="text-muted" style="font-size:0.65rem">Mín: ${p.estoque_minimo}</span>
                 <strong class="${isZero ? 'text-danger' : 'text-warning'}" style="font-size:0.8rem">${p.estoque_atual} <span class="fw-normal text-muted" style="font-size:0.7rem">${p.unidade}</span></strong>
             </div>
           </div>
        </div>
        `;
        }).join("") + `</div>`;
    }

  } catch (error) {
    if (window.ui) ui.showToast("Falha em Dashboard: " + error.message, "danger");
  }
};
