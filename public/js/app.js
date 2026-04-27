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

function enforceIntegerInput(input, options = {}) {
    if (!input) return;

    const min = options.min ?? null;

    const sanitize = () => {
        let value = input.value.replace(/[^\d-]/g, "");

        if (min !== null && min >= 0) {
            value = value.replace(/-/g, "");
        } else if (value.includes("-")) {
            value = `${value.startsWith("-") ? "-" : ""}${value.replace(/-/g, "")}`;
        }

        input.value = value;
    };

    input.addEventListener("input", sanitize);
    input.addEventListener("keydown", (event) => {
        if (["e", "E", ".", ",", "+"].includes(event.key)) {
            event.preventDefault();
        }
    });
    input.addEventListener("blur", () => {
        sanitize();
        if (!input.value) return;

        const parsed = Number.parseInt(input.value, 10);
        if (Number.isNaN(parsed)) {
            input.value = "";
            return;
        }

        if (min !== null && parsed < min) {
            input.value = String(min);
            return;
        }

        input.value = String(parsed);
    });
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
    showConfirm: function (options = {}) {
        return new Promise((resolve) => {
            const {
                title = "Confirmar ação",
                message = "Tem certeza que deseja continuar?",
                confirmText = "Confirmar",
                cancelText = "Cancelar",
                confirmClass = "btn-primary",
                icon = "bi-question-circle text-primary",
                danger = false
            } = options;

            const id = 'confirm-' + Date.now();
            const iconClass = danger ? "bi-exclamation-triangle text-danger" : icon;
            const finalConfirmClass = danger ? "btn-danger" : confirmClass;

            const html = `
                <div class="modal fade" id="${id}" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog modal-dialog-centered modal-sm">
                        <div class="modal-content border-0 shadow-lg">
                            <div class="modal-header border-bottom-0 pb-0 pt-4 px-4">
                                <div class="d-flex align-items-center gap-3">
                                    <div class="confirm-icon">
                                        <i class="bi ${iconClass}"></i>
                                    </div>
                                    <h5 class="modal-title fw-bold mb-0" id="${id}-label">${escapeHtml(title)}</h5>
                                </div>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
                            </div>
                            <div class="modal-body px-4 pb-2 pt-2">
                                <p class="text-secondary mb-0" style="font-size:0.9rem">${escapeHtml(message)}</p>
                            </div>
                            <div class="modal-footer border-top-0 pt-2 pb-4 px-4">
                                <button type="button" class="btn btn-secondary px-4" data-bs-dismiss="modal" id="${id}-cancel">${escapeHtml(cancelText)}</button>
                                <button type="button" class="btn ${finalConfirmClass} px-4" id="${id}-confirm">${escapeHtml(confirmText)}</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            const host = document.getElementById("app-modals") || document.body;
            host.insertAdjacentHTML('beforeend', html);

            const modalEl = document.getElementById(id);
            const modal = new bootstrap.Modal(modalEl);

            const cleanup = () => {
                modalEl.remove();
            };

            document.getElementById(`${id}-confirm`).addEventListener('click', () => {
                cleanup();
                resolve(true);
            });

            document.getElementById(`${id}-cancel`).addEventListener('click', () => {
                resolve(false);
            });

            modalEl.addEventListener('hidden.bs.modal', () => {
                resolve(false);
            });

            modal.show();
        });
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
window.enforceIntegerInput = enforceIntegerInput;
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
