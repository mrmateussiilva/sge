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
    }
};

function initApp() {
    if (typeof protegerPagina === "function") {
        const isLogged = protegerPagina();
        if (!isLogged) return;
    }
    initSidebar();
    if (typeof handleRoute === "function") {
        handleRoute();
    }
}

document.addEventListener("DOMContentLoaded", initApp);
