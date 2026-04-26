(function initLayout() {
  const STORAGE_KEY = "sge-sidebar-collapsed";
  const toggleButton = document.getElementById("sidebarToggle");
  const closeTargets = document.querySelectorAll("[data-sidebar-close]");
  const mobileQuery = window.matchMedia("(max-width: 991.98px)");

  function syncCollapsedClass(collapsed) {
    document.body.classList.toggle("sidebar-collapsed", collapsed);
    document.documentElement.classList.toggle("sidebar-collapsed", collapsed);
  }

  function applyDesktopState() {
    if (mobileQuery.matches) {
      syncCollapsedClass(false);
      document.documentElement.classList.remove("layout-pending");
      return;
    }

    const collapsed = localStorage.getItem(STORAGE_KEY) === "true";
    syncCollapsedClass(collapsed);
    document.documentElement.classList.remove("layout-pending");
  }

  function closeMobileSidebar() {
    document.body.classList.remove("sidebar-open");
  }

  function toggleSidebar() {
    if (mobileQuery.matches) {
      document.body.classList.toggle("sidebar-open");
      return;
    }

    const collapsed = !document.body.classList.contains("sidebar-collapsed");
    syncCollapsedClass(collapsed);
    localStorage.setItem(STORAGE_KEY, String(collapsed));
  }

  if (toggleButton) {
    toggleButton.addEventListener("click", toggleSidebar);
  }

  closeTargets.forEach((element) => {
    element.addEventListener("click", closeMobileSidebar);
  });

  mobileQuery.addEventListener("change", () => {
    closeMobileSidebar();
    applyDesktopState();
  });

  applyDesktopState();
})();
