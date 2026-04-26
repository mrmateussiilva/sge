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

function initApp() {
    // Proteger pagina check if token exists
    if (typeof protegerPagina === "function") {
        const isLogged = protegerPagina();
        if (!isLogged) return; // Wait for redirect to login.html
    }

    // Initialize UI scripts
    initSidebar();

    // Call the initial route
    if (typeof handleRoute === "function") {
        handleRoute();
    }
}

// When document is loaded, initialize
document.addEventListener("DOMContentLoaded", initApp);
