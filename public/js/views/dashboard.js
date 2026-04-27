/* js/views/dashboard.js */
window.renderDashboard = async function () {
  const appContent = document.getElementById("app-content");

  appContent.innerHTML = `
    <section class="page-shell">
      <header class="page-hero">
        <div class="page-hero-copy">
          <span class="page-kicker">Centro de controle</span>
          <h1 class="page-title">Operação diária do estoque</h1>
          <p class="page-subtitle">
            Acompanhe a saúde do acervo, os lançamentos mais recentes e os itens que exigem atenção imediata.
          </p>
        </div>
        <div class="page-actions">
          <span class="page-meta">Sincronização: <strong>agora</strong></span>
          <button class="btn btn-light border bg-white shadow-sm" id="dashboardRefreshBtn" title="Atualizar dados">
            <i class="bi bi-arrow-clockwise me-2"></i> Atualizar painel
          </button>
        </div>
      </header>

      <div class="row g-3" id="dash-metrics">
        <div class="col-xl-3 col-sm-6"><div class="card-enterprise metric-card"><div class="skeleton w-100" style="height: 120px;"></div></div></div>
        <div class="col-xl-3 col-sm-6"><div class="card-enterprise metric-card"><div class="skeleton w-100" style="height: 120px;"></div></div></div>
        <div class="col-xl-3 col-sm-6"><div class="card-enterprise metric-card"><div class="skeleton w-100" style="height: 120px;"></div></div></div>
        <div class="col-xl-3 col-sm-6"><div class="card-enterprise metric-card"><div class="skeleton w-100" style="height: 120px;"></div></div></div>
      </div>

      <div class="row g-3">
        <div class="col-xl-8">
          <section class="card-enterprise surface-panel h-100 d-flex flex-column">
            <div class="card-header-polished px-4 py-3 d-flex justify-content-between align-items-center">
              <div>
                <div class="panel-title">Fluxo recente</div>
                <small class="text-muted">Últimos movimentos registrados na operação</small>
              </div>
              <a href="#/movimentacoes" class="btn btn-light border bg-white table-toolbar-link">Abrir histórico</a>
            </div>
            <div class="flex-grow-1 p-0 overflow-auto">
              <div class="table-responsive h-100">
                <table class="table table-compact mb-0 border-0">
                  <thead class="position-sticky top-0" style="z-index: 1;">
                    <tr>
                      <th class="border-start-0 ps-4">Momento</th>
                      <th>Produto</th>
                      <th class="text-center">Tipo</th>
                      <th class="text-end">Quantidade</th>
                      <th class="text-end pe-4">Saldo</th>
                    </tr>
                  </thead>
                  <tbody id="dash-movimentacoes">
                    <tr><td colspan="5" class="p-4"><div class="skeleton w-100 mb-2" style="height: 56px;"></div></td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </div>

        <div class="col-xl-4">
          <section class="card-enterprise surface-panel h-100 d-flex flex-column">
            <div class="card-header-polished px-4 py-3">
              <div class="panel-title">Itens críticos</div>
              <small class="text-muted">Produtos abaixo do ponto mínimo ou sem saldo.</small>
            </div>
            <div class="flex-grow-1 overflow-y-auto" id="dash-alertas">
              <div class="p-4"><div class="skeleton w-100 mb-2" style="height: 56px;"></div></div>
            </div>
          </section>
        </div>
      </div>
    </section>
  `;

  const refreshBtn = document.getElementById("dashboardRefreshBtn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => window.renderDashboard());
  }

  try {
    const [dashboard, produtos] = await Promise.all([window.api.getDashboard(), window.api.getProdutos()]);

    const zeros = produtos.filter((p) => p.estoque_atual === 0).length;
    const lowStock = Math.max(dashboard.produtos_com_estoque_baixo.length - zeros, 0);
    const healthy = Math.max(produtos.length - dashboard.produtos_com_estoque_baixo.length, 0);

    document.getElementById("dash-metrics").innerHTML = `
      <div class="col-xl-3 col-sm-6">
        <article class="card-enterprise metric-card metric-card-primary">
          <div class="metric-card-header">
            <span class="metric-card-label">Acervo total</span>
            <span class="metric-card-icon"><i class="bi bi-box-seam"></i></span>
          </div>
          <h3 class="metric-card-value">${dashboard.total_produtos}</h3>
          <div class="metric-card-note">Itens ativos disponíveis no catálogo operacional.</div>
        </article>
      </div>
      <div class="col-xl-3 col-sm-6">
        <article class="card-enterprise metric-card metric-card-success">
          <div class="metric-card-header">
            <span class="metric-card-label">Situação saudável</span>
            <span class="metric-card-icon"><i class="bi bi-check2-circle"></i></span>
          </div>
          <h3 class="metric-card-value">${healthy}</h3>
          <div class="metric-card-note">Produtos operando acima do estoque mínimo definido.</div>
        </article>
      </div>
      <div class="col-xl-3 col-sm-6">
        <article class="card-enterprise metric-card metric-card-warning">
          <div class="metric-card-header">
            <span class="metric-card-label">Baixo estoque</span>
            <span class="metric-card-icon"><i class="bi bi-exclamation-triangle"></i></span>
          </div>
          <h3 class="metric-card-value">${lowStock}</h3>
          <div class="metric-card-note">Itens que pedem reposição antes de entrarem em ruptura.</div>
        </article>
      </div>
      <div class="col-xl-3 col-sm-6">
        <article class="card-enterprise metric-card metric-card-danger">
          <div class="metric-card-header">
            <span class="metric-card-label">Ruptura</span>
            <span class="metric-card-icon"><i class="bi bi-slash-circle"></i></span>
          </div>
          <h3 class="metric-card-value">${zeros}</h3>
          <div class="metric-card-note">Produtos zerados, sem saldo disponível para novas saídas.</div>
        </article>
      </div>
    `;

    const formatData = (value) => {
      const date = new Date(value);
      return `
        <strong class="text-dark d-block mb-0 lh-1" style="font-size:0.82rem">${date.toLocaleDateString("pt-BR")}</strong>
        <span class="text-muted font-monospace d-flex align-items-center gap-1 mt-1" style="font-size:0.68rem">
          <i class="bi bi-clock"></i>${date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
        </span>
      `;
    };

    const movTable = document.getElementById("dash-movimentacoes");
    if (dashboard.ultimas_movimentacoes.length === 0) {
      movTable.innerHTML = `
        <tr>
          <td colspan="5" class="py-5">
            <div class="empty-state">
              <i class="bi bi-inboxes empty-icon d-block"></i>
              <h6 class="fw-bold text-dark mb-1">Nenhum lançamento recente</h6>
              <small class="text-muted">O histórico operacional ainda não recebeu movimentações.</small>
            </div>
          </td>
        </tr>
      `;
    } else {
      movTable.innerHTML = dashboard.ultimas_movimentacoes.slice(0, 6).map((mov) => {
        let badgeClass = "ok";
        let label = "Entrada";
        let sign = "+";
        let qtyColor = "text-success";

        if (mov.tipo === "saida") {
          badgeClass = "zero";
          label = "Saída";
          sign = "-";
          qtyColor = "text-danger";
        } else if (mov.tipo === "ajuste") {
          badgeClass = "low";
          label = "Ajuste";
          sign = "";
          qtyColor = "text-primary";
        }

        return `
          <tr>
            <td class="ps-4 align-middle" style="width: 20%">${formatData(mov.created_at)}</td>
            <td class="align-middle" style="width: 36%">
              <div class="fw-bold text-dark text-truncate lh-1 mb-1" style="font-size: 0.88rem; max-width: 260px;" title="${mov.produto.nome}">${mov.produto.nome}</div>
              <span class="text-muted font-monospace" style="font-size: 0.68rem;">${mov.produto.sku}</span>
            </td>
            <td class="align-middle text-center" style="width: 16%">
              <div class="badge-status ${badgeClass}">
                <span class="dot"></span>${label}
              </div>
            </td>
            <td class="align-middle text-end" style="width: 14%">
              <span class="fw-bold fs-6 lh-1 ${qtyColor}">${sign}${mov.quantidade}</span>
            </td>
            <td class="align-middle text-end pe-4" style="width: 14%">
              <span class="text-muted d-block" style="font-size: 0.68rem;">Saldo atual</span>
              <strong class="text-dark">${mov.produto.estoque_atual}</strong>
              <small class="text-muted">${mov.produto.unidade}</small>
            </td>
          </tr>
        `;
      }).join("");
    }

    const alertas = document.getElementById("dash-alertas");
    if (dashboard.produtos_com_estoque_baixo.length === 0) {
      alertas.innerHTML = `
        <div class="empty-state py-5">
          <i class="bi bi-shield-check empty-icon d-block text-success"></i>
          <h6 class="fw-bold text-dark mb-1">Sem alertas ativos</h6>
          <small class="text-muted">Nenhum produto está abaixo do mínimo configurado.</small>
        </div>
      `;
    } else {
      alertas.innerHTML = `
        <ul class="list-group list-group-flush mb-0 dashboard-alert-list">
          ${dashboard.produtos_com_estoque_baixo.map((produto) => {
            const isZero = produto.estoque_atual === 0;
            return `
              <li class="list-group-item d-flex justify-content-between align-items-center gap-3">
                <div class="d-flex align-items-start gap-3 min-vw-0">
                  <span class="metric-card-icon ${isZero ? "bg-danger-subtle text-danger" : "bg-warning-subtle"}" style="width: 40px; height: 40px; border-radius: 14px; font-size: 0.95rem;">
                    <i class="bi ${isZero ? "bi-slash-circle" : "bi-exclamation-triangle"}"></i>
                  </span>
                  <div class="min-vw-0">
                    <div class="fw-bold text-dark text-truncate mb-1" style="max-width: 220px; font-size: 0.85rem;" title="${produto.nome}">${produto.nome}</div>
                    <div class="text-muted font-monospace" style="font-size: 0.68rem;">${produto.sku}</div>
                  </div>
                </div>
                <div class="text-end flex-shrink-0">
                  <div class="fw-bold ${isZero ? "text-danger" : ""}" style="font-size: 0.95rem;">${produto.estoque_atual}</div>
                  <div class="text-muted" style="font-size: 0.7rem;">mín. ${produto.estoque_minimo}</div>
                </div>
              </li>
            `;
          }).join("")}
        </ul>
      `;
    }
  } catch (error) {
    if (window.ui) {
      ui.showToast("Falha em Dashboard: " + ui.getErrorMessage(error), "danger");
      ui.renderPageError(appContent, {
        title: "Dashboard indisponível no momento",
        message: "Não foi possível montar a visão geral com os dados atuais.",
        details: ui.getErrorMessage(error),
        actionLabel: "Recarregar dashboard",
        action: "window.renderDashboard()"
      });
    }
  }
};
