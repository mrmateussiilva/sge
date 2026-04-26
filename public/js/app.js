/* js/app.js */
function initSidebar() {
    const toggleBtn = document.getElementById("sidebarToggle");
    const STORAGE_KEY = "sge-sidebar";

    if (toggleBtn) {
        toggleBtn.addEventListener("click", () => {
            const isCollapsed = document.documentElement.classList.toggle("sidebar-collapsed");
            localStorage.setItem(STORAGE_KEY, isCollapsed ? "collapsed" : "expanded");
        });
    }
}

function escapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function normalizeErrorMessage(error, fallback = "Ocorreu um erro inesperado. Tente novamente.") {
    if (!error) return fallback;
    if (typeof error === "string" && error.trim()) return error.trim();
    if (error.message && String(error.message).trim()) return String(error.message).trim();
    return fallback;
}

function buildErrorStateHTML(options = {}) {
    const {
        title = "Não foi possível concluir esta operação",
        message = "Ocorreu um erro inesperado. Tente novamente.",
        details = "",
        icon = "bi-exclamation-octagon",
        compact = false,
        actionLabel = "Tentar novamente",
        action = "window.location.reload()"
    } = options;

    const detailBlock = details
        ? `<div class="error-state-details">${escapeHtml(details)}</div>`
        : "";

    return `
      <section class="error-state ${compact ? "error-state-compact" : ""}" role="alert">
        <div class="error-state-icon">
          <i class="bi ${icon}"></i>
        </div>
        <div class="error-state-content">
          <span class="error-state-kicker">Falha de execução</span>
          <h3>${escapeHtml(title)}</h3>
          <p>${escapeHtml(message)}</p>
          ${detailBlock}
          <div class="error-state-actions">
            <button class="btn btn-primary" type="button" onclick="${action}">
              <i class="bi bi-arrow-clockwise me-2"></i>${escapeHtml(actionLabel)}
            </button>
          </div>
        </div>
      </section>
    `;
}

window.ui = {
    showToast: function (message, type = 'success') {
        const container = document.getElementById("toast-container");
        if (!container) return;
        const id = 'toast-' + Date.now();
        const icon = type === 'success' ? 'bi-check-circle-fill' : (type === 'danger' ? 'bi-exclamation-triangle-fill' : 'bi-info-circle-fill');
        let color = 'text-info';
        if (type === 'success') color = 'text-success';
        if (type === 'danger') color = 'text-danger';

        const toastHTML = `
       <div id="${id}" class="toast align-items-center bg-white border shadow-md mb-2" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="4000">
         <div class="d-flex">
           <div class="toast-body d-flex align-items-center gap-3">
             <i class="bi ${icon} ${color} fs-5"></i>
             <span class="fw-medium text-dark" style="font-size:0.9rem">${message}</span>
           </div>
           <button type="button" class="btn-close me-3 m-auto" data-bs-dismiss="toast" aria-label="Fechar"></button>
         </div>
       </div>
     `;
        container.insertAdjacentHTML('beforeend', toastHTML);
        const toastEl = document.getElementById(id);
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
        toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
    },
    getErrorMessage: function (error, fallback) {
        return normalizeErrorMessage(error, fallback);
    },
    renderPageError: function (container, options = {}) {
        if (!container) return;
        container.innerHTML = buildErrorStateHTML(options);
    },
    renderInlineError: function (container, options = {}) {
        if (!container) return;
        if (options.tableCols) {
            container.innerHTML = `
              <tr>
                <td colspan="${options.tableCols}" class="p-3">
                  ${buildErrorStateHTML({ ...options, compact: true })}
                </td>
              </tr>
            `;
            return;
        }
        container.innerHTML = `
          <div class="inline-error-wrap">
            ${buildErrorStateHTML({ ...options, compact: true })}
          </div>
        `;
    }
};

function installGlobalErrorHandlers() {
    const renderUnexpectedError = (error) => {
        const appContent = document.getElementById("app-content");
        if (!appContent || !window.ui) return;

        window.ui.renderPageError(appContent, {
            title: "A interface encontrou uma falha inesperada",
            message: "O módulo atual foi interrompido antes de terminar o carregamento.",
            details: normalizeErrorMessage(error),
            icon: "bi-bug",
            actionLabel: "Recarregar módulo",
            action: "window.handleRoute ? window.handleRoute() : window.location.reload()"
        });
    };

    window.addEventListener("error", (event) => {
        renderUnexpectedError(event.error || event.message);
    });

    window.addEventListener("unhandledrejection", (event) => {
        renderUnexpectedError(event.reason);
    });
}

window.escapeHtml = escapeHtml;
window.normalizeErrorMessage = normalizeErrorMessage;
window.buildErrorStateHTML = buildErrorStateHTML;

function initApp() {
    if (typeof protegerPagina === "function") {
        const isLogged = protegerPagina();
        if (!isLogged) return;
    }
    installGlobalErrorHandlers();
    initSidebar();
    if (typeof handleRoute === "function") {
        handleRoute();
    }
}

document.addEventListener("DOMContentLoaded", initApp);
