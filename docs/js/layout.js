(function initLayout() {
  const STORAGE_KEY = "sge-sidebar-collapsed";
  const toggleButton = document.getElementById("sidebarToggle");
  const closeTargets = document.querySelectorAll("[data-sidebar-close]");
  const mobileQuery = window.matchMedia("(max-width: 991.98px)");

  function applyDesktopState() {
    if (mobileQuery.matches) {
      document.body.classList.remove("sidebar-collapsed");
      return;
    }

    const collapsed = localStorage.getItem(STORAGE_KEY) === "true";
    document.body.classList.toggle("sidebar-collapsed", collapsed);
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
    document.body.classList.toggle("sidebar-collapsed", collapsed);
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
