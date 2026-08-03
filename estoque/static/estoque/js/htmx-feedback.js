document.addEventListener('sge:feedback', function (event) {
    const detail = event.detail || {};
    if (detail.message && typeof window.showToast === 'function') {
        window.showToast(detail.message, detail.type || 'success');
    }
});

document.addEventListener('htmx:afterSwap', function (event) {
    const modalElement = event.detail.target.querySelector('[data-sge-modal-autoshow]');
    if (modalElement && window.bootstrap) {
        window.bootstrap.Modal.getOrCreateInstance(modalElement).show();
    }
});

document.addEventListener('sge:modal-close', function (event) {
    const modalElement = document.getElementById((event.detail || {}).id);
    if (modalElement && window.bootstrap) {
        window.bootstrap.Modal.getOrCreateInstance(modalElement).hide();
    }
});
