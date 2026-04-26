/* js/views/dashboard.js */
window.renderDashboard = async function () {
  const appContent = document.getElementById("app-content");

  appContent.innerHTML = `
    <!-- Minimal Header -->
    <header class="mb-3 d-flex flex-column flex-md-row justify-content-between align-items-md-end gap-2">
      <div>
        <h1 class="page-title fs-4 fw-bold mb-0 text-dark">Dashboard</h1>
        <p class="text-secondary small mb-0 mt-1">Visão geral e resumo operacional</p>
      </div>
      <div class="d-flex align-items-center gap-2">
        <span class="text-muted d-none d-sm-inline" style="font-size: 0.75rem;">Última atualização: <strong>agora</strong></span>
        <button class="btn btn-light shadow-sm border bg-white flex-shrink-0 d-flex align-items-center justify-content-center" onclick="window.renderDashboard()" title="Atualizar dados" style="height: var(--input-height); padding: 0 12px; font-size: 0.85rem;">
          <i class="bi bi-arrow-clockwise me-1"></i> Recarregar
        </button>
      </div>
    </header>

    <!-- 4 Metric Cards Container -->
    <div class="row g-2 mb-3" id="dash-metrics">
       <!-- Skeletons while loading -->
       <div class="col-12"><div class="skeleton rounded-3" style="height: 86px; width: 100%;"></div></div>
    </div>

    <!-- 2 Column Layout (65% / 35%) -->
    <div class="row g-2 mb-3">
      
      <!-- Left: Recent Lançamentos -->
      <div class="col-lg-8">
        <div class="card-enterprise h-100 d-flex flex-column bg-white border shadow-sm" style="border-radius: var(--radius-md);">
          <div class="card-header-polished border-bottom px-3 py-2 d-flex justify-content-between align-items-center bg-white" style="border-top-left-radius: var(--radius-md); border-top-right-radius: var(--radius-md);">
            <h6 class="fw-bold mb-0 text-dark" style="font-size:0.85rem">Lançamentos Recentes</h6>
            <a href="#/movimentacoes" class="btn btn-sm btn-light border bg-white shadow-sm fw-medium px-2 py-1" style="font-size:0.75rem;">Ver Tudo</a>
          </div>
          <div class="flex-grow-1 p-0 overflow-auto" style="border-bottom-left-radius: var(--radius-md); border-bottom-right-radius: var(--radius-md);">
            <div class="table-responsive h-100">
              <table class="table table-compact mb-0 border-0">
                <thead class="position-sticky top-0 bg-white" style="z-index: 1;">
                  <tr>
                    <th class="border-top-0 border-start-0 ps-3 text-dark" style="background-color: #f8f9fa;">Data</th>
                    <th class="border-top-0 text-dark" style="background-color: #f8f9fa;">Produto</th>
                    <th class="border-top-0 text-center text-dark" style="background-color: #f8f9fa;">Operação</th>
                    <th class="border-top-0 text-end text-dark" style="background-color: #f8f9fa;">Qtd.</th>
                    <th class="border-top-0 text-end text-dark pe-3" style="background-color: #f8f9fa;">Resumo</th>
                  </tr>
                </thead>
                <tbody id="dash-movimentacoes">
                   <tr><td colspan="5" class="p-4"><div class="skeleton w-100 mb-2" style="height: 48px;"></div></td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Right: Demandam Atenção -->
      <div class="col-lg-4">
        <div class="card-enterprise h-100 d-flex flex-column bg-white border shadow-sm" style="border-radius: var(--radius-md);">
          <div class="card-header-polished border-bottom px-3 py-2 bg-white" style="border-top-left-radius: var(--radius-md); border-top-right-radius: var(--radius-md);">
            <h6 class="fw-bold mb-0 text-dark" style="font-size:0.85rem">Demandam Atenção</h6>
          </div>
          <div class="flex-grow-1 p-0 overflow-y-auto bg-white" id="dash-alertas" style="max-height: 420px; border-bottom-left-radius: var(--radius-md); border-bottom-right-radius: var(--radius-md);">
             <div class="p-3"><div class="skeleton w-100 mb-2" style="height: 48px;"></div></div>
          </div>
        </div>
      </div>
      
    </div>
  `;

  try {
    const [dashboard, produtos] = await Promise.all([window.api.getDashboard(), window.api.getProdutos()]);

    const zeros = produtos.filter(p => p.estoque_atual === 0).length;
    const ok = produtos.length - dashboard.produtos_com_estoque_baixo.length;

    // Render Metrics
    document.getElementById("dash-metrics").innerHTML = `
      <div class="col-xl-3 col-sm-6">
        <div class="card-enterprise h-100 p-3 bg-white border shadow-sm d-flex justify-content-between align-items-center" style="border-left: 3px solid var(--primary) !important;">
          <div>
            <span class="text-secondary fw-bold text-uppercase d-block mb-1" style="font-size:0.65rem; letter-spacing: 0.05em;">Acervo Total</span>
            <h3 class="fw-bold text-dark mb-0 fs-4 lh-1">${dashboard.total_produtos}</h3>
          </div>
          <div class="bg-primary-subtle text-primary rounded-2 d-flex align-items-center justify-content-center" style="width: 36px; height: 36px;">
            <i class="bi bi-box-seam" style="font-size: 1rem;"></i>
          </div>
        </div>
      </div>
      <div class="col-xl-3 col-sm-6">
        <div class="card-enterprise h-100 p-3 bg-white border shadow-sm d-flex justify-content-between align-items-center" style="border-left: 3px solid var(--success) !important;">
          <div>
            <span class="text-secondary fw-bold text-uppercase d-block mb-1" style="font-size:0.65rem; letter-spacing: 0.05em;">Saudável</span>
            <h3 class="fw-bold text-dark mb-0 fs-4 lh-1">${ok}</h3>
          </div>
          <div class="bg-success-subtle text-success rounded-2 d-flex align-items-center justify-content-center" style="width: 36px; height: 36px;">
            <i class="bi bi-check2-circle" style="font-size: 1rem;"></i>
          </div>
        </div>
      </div>
      <div class="col-xl-3 col-sm-6">
        <div class="card-enterprise h-100 p-3 bg-white border shadow-sm d-flex justify-content-between align-items-center" style="border-left: 3px solid #f1c21b !important;">
          <div>
            <span class="text-secondary fw-bold text-uppercase d-block mb-1" style="font-size:0.65rem; letter-spacing: 0.05em;">Baixo Estoque</span>
            <h3 class="fw-bold text-dark mb-0 fs-4 lh-1">${dashboard.produtos_com_estoque_baixo.length - zeros}</h3>
          </div>
          <div class="bg-warning-subtle text-warning-dark rounded-2 d-flex align-items-center justify-content-center" style="width: 36px; height: 36px; color: #b38600;">
            <i class="bi bi-exclamation-triangle" style="font-size: 1rem; color: #a67c00;"></i>
          </div>
        </div>
      </div>
      <div class="col-xl-3 col-sm-6">
        <div class="card-enterprise h-100 p-3 bg-white border shadow-sm d-flex justify-content-between align-items-center" style="border-left: 3px solid var(--danger) !important;">
          <div>
            <span class="text-secondary fw-bold text-uppercase d-block mb-1" style="font-size:0.65rem; letter-spacing: 0.05em;">Zerados</span>
            <h3 class="fw-bold text-dark mb-0 fs-4 lh-1">${zeros}</h3>
          </div>
          <div class="bg-danger-subtle text-danger rounded-2 d-flex align-items-center justify-content-center" style="width: 36px; height: 36px;">
            <i class="bi bi-dash-circle" style="font-size: 1rem;"></i>
          </div>
        </div>
      </div>
    `;

    // formatData helper
    const formatData = (d) => {
      const dt = new Date(d);
      return `<strong class="text-dark d-block mb-0 lh-1" style="font-size:0.80rem">${dt.toLocaleDateString("pt-BR")}</strong><span class="text-muted font-monospace d-flex align-items-center gap-1 mt-1" style="font-size:0.68rem"><i class="bi bi-clock"></i> ${dt.toLocaleTimeString("pt-BR", { hour: '2-digit', minute: '2-digit' })}</span>`;
    };

    const movTable = document.getElementById("dash-movimentacoes");
    if (dashboard.ultimas_movimentacoes.length === 0) {
      movTable.innerHTML = `<tr><td colspan="5" class="py-4"><div class="d-flex flex-column justify-content-center align-items-center text-muted"><i class="bi bi-inboxes mb-1" style="font-size: 1.5rem;"></i><h6 class="fw-bold fs-6 mb-0 text-dark">Nenhum lançamento</h6><small style="font-size: 0.75rem;">Histórico operacional vazio.</small></div></td></tr>`;
    } else {
      movTable.innerHTML = dashboard.ultimas_movimentacoes.slice(0, 6).map(m => {
        let badgeClass = "ok", lbl = "Entrada", sign = "+", resColor = "text-success";
        if (m.tipo === "saida") { badgeClass = "zero"; lbl = "Saída"; sign = "-"; resColor = "text-danger"; }
        else if (m.tipo === "ajuste") { badgeClass = "low"; lbl = "Ajuste"; sign = ""; resColor = "text-primary"; }

        const badgeStatus = `<div class="badge-status ${badgeClass} px-2 py-1" style="border: none; padding: 2px 6px !important; font-size: 0.65rem;"><span class="dot"></span> ${lbl}</div>`;

        return `
         <tr>
           <td class="ps-3 align-middle" style="width: 18%">${formatData(m.created_at)}</td>
           <td class="align-middle" style="width: 35%;">
             <div class="fw-bold text-dark text-truncate mb-0 lh-1" style="font-size: 0.85rem; max-width: 220px;" title="${m.produto.nome}">${m.produto.nome}</div>
             <span class="text-muted font-monospace" style="font-size:0.65rem;">${m.produto.sku}</span>
           </td>
           <td class="align-middle text-center" style="width: 17%">
             ${badgeStatus}
           </td>
           <td class="align-middle text-end" style="width: 15%">
             <span class="fw-bold fs-6 lh-1 ${resColor}">${sign}${m.quantidade}</span>
           </td>
           <td class="pe-3 align-middle text-end text-muted" style="width: 15%; font-size: 0.75rem;">
               <span class="d-block lh-1">Estq:</span>
               <strong class="text-dark">${m.produto.estoque_atual}</strong> <small class="fw-normal" style="font-size: 0.65rem">${m.produto.unidade}</small>
           </td>
         </tr>
       `}).join("");
    }

    // Render Demandam Atenção Panel
    const alertas = document.getElementById("dash-alertas");
    if (dashboard.produtos_com_estoque_baixo.length === 0) {
      alertas.innerHTML = `<div class="d-flex flex-column justify-content-center align-items-center text-muted p-4"><i class="bi bi-shield-check text-success mb-1" style="font-size: 1.5rem;"></i><h6 class="fw-bold fs-6 mb-0 text-dark">Acervo Saudável</h6><small class="text-center" style="font-size: 0.75rem;">Nenhum produto abaixo do mínimo.</small></div>`;
    } else {
      alertas.innerHTML = `<ul class="list-group list-group-flush mb-0">` +
        dashboard.produtos_com_estoque_baixo.map(p => {
          const isZero = p.estoque_atual === 0;
          return `
        <li class="list-group-item d-flex justify-content-between align-items-center p-2 px-3 border-bottom bg-white">
            <div class="d-flex align-items-center gap-2" style="min-width: 0;">
                <i class="bi ${isZero ? 'bi-x-circle-fill text-danger' : 'bi-exclamation-triangle-fill text-warning'}" style="font-size: 0.85rem;"></i>
                <div class="d-flex flex-column" style="min-width: 0;">
                    <div class="fw-bold text-dark text-truncate mb-0 lh-1" style="font-size: 0.82rem; max-width: 180px;" title="${p.nome}">${p.nome}</div>
                    <span class="text-muted font-monospace" style="font-size: 0.65rem;">${p.sku}</span>
                </div>
            </div>
            <div class="text-end d-flex flex-column align-items-end pe-1">
               <span class="lh-1 text-muted mb-1" style="font-size: 0.65rem;">Atu: <strong class="${isZero ? 'text-danger' : 'text-warning-dark'}" style="color: ${!isZero ? '#a67c00' : ''}">${p.estoque_atual}</strong></span>
               <span class="lh-1 text-muted" style="font-size: 0.65rem;">Mín: <strong>${p.estoque_minimo}</strong></span>
            </div>
        </li>
        `;
        }).join("") + `</ul>`;
    }

  } catch (error) {
    if (window.ui) ui.showToast("Falha em Dashboard: " + error.message, "danger");
    document.getElementById("app-content").innerHTML += `<div class="alert alert-danger m-3 border-0 bg-danger-subtle">${error.message}</div>`;
  }
};
