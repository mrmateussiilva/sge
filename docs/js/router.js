/* js/router.js */
const appContent = document.getElementById("app-content");

const routes = {
    "#/dashboard": "renderDashboard",
    "#/produtos": "renderProdutos",
    "#/movimentacoes": "renderMovimentacoes",
};

async function handleRoute() {
    let hash = window.location.hash;

    if (!hash || hash === "#/" || hash === "#") {
        hash = "#/dashboard";
        window.location.hash = hash;
        return;
    }

    // Highlight active menu item
    document.querySelectorAll(".nav-item").forEach(item => item.classList.remove("active"));
    const activeLink = document.querySelector(`.nav-item[href="${hash}"]`);
    if (activeLink) {
        activeLink.classList.add("active");
    }

    // Find view render function
    const renderFunctionName = routes[hash];
    if (renderFunctionName && typeof window[renderFunctionName] === "function") {
        // Show a small loader while rendering
        appContent.innerHTML = `
      <div class="d-flex align-items-center justify-content-center h-100 w-100" style="min-height:300px;">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    `;
        try {
            await window[renderFunctionName]();
        } catch (err) {
            console.error(err);
            appContent.innerHTML = `
        <div class="alert alert-danger m-4">
          <h5>Erro ao carregar a página</h5>
          <p>${err.message}</p>
        </div>
      `;
        }
    } else {
        appContent.innerHTML = `
      <div class="empty-state m-auto">
        <div class="empty-state-icon fs-1 text-muted mb-3"><i class="bi bi-exclamation-triangle"></i></div>
        <h4 class="fw-bold">Página não encontrada</h4>
        <p class="text-secondary">O endereço que você tentou acessar não existe.</p>
        <button class="btn btn-primary mt-2" onclick="window.location.hash='#/dashboard'">Voltar ao Dashboard</button>
      </div>
    `;
    }
}

window.addEventListener("hashchange", handleRoute);
