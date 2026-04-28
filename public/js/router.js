/* js/router.js */
const appContent = document.getElementById("app-content");

const routes = {
  "#/dashboard": { fn: "renderDashboard", title: "SGE | Dashboard" },
  "#/produtos": { fn: "renderProdutos", title: "SGE | Produtos" },
  "#/categorias": { fn: "renderCategorias", title: "SGE | Categorias" },
  "#/tags": { fn: "renderTags", title: "SGE | Tags" },
  "#/movimentacoes": { fn: "renderMovimentacoes", title: "SGE | Movimentações" },
  "#/importar-xml": { fn: "renderImportarXml", title: "SGE | Importar NF-e" },
  "#/usuarios": { fn: "renderUsuarios", title: "SGE | Usuários" },
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
  const routeObj = routes[hash];

  if (routeObj && typeof window[routeObj.fn] === "function") {
    document.title = routeObj.title;

    // Elegant loading state wrapper
    appContent.innerHTML = `
      <div class="d-flex flex-column align-items-center justify-content-center h-100 w-100" style="min-height:400px;">
        <div class="spinner-border text-primary mb-3" role="status" style="width: 2rem; height: 2rem;"></div>
        <span class="text-secondary fw-medium">Carregando módulo...</span>
      </div>
    `;
    try {
      await window[routeObj.fn]();
    } catch (err) {
      console.error(err);
      if (window.ui) {
        window.ui.renderPageError(appContent, {
          title: "Erro ao exibir a página",
          message: "O módulo não conseguiu carregar os dados necessários.",
          details: window.ui.getErrorMessage(err),
          actionLabel: "Tentar novamente",
          action: "window.handleRoute()"
        });
      }
    }
  } else {
    document.title = "SGE | Página não encontrada";
    appContent.innerHTML = `
      <div class="card-enterprise p-5 text-center empty-state m-auto w-100" style="max-width:500px">
        <i class="bi bi-search text-muted display-4 mb-3 d-block"></i>
        <h4 class="fw-bold text-dark">Página não encontrada</h4>
        <p class="text-secondary">O endereço que você procurou não foi identificado no sistema.</p>
        <button class="btn btn-primary mt-2 px-4" onclick="window.location.hash='#/dashboard'">Voltar ao Início</button>
      </div>
    `;
  }
}

window.addEventListener("hashchange", handleRoute);
window.handleRoute = handleRoute;
